from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from prettytable import PrettyTable, TableStyle
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from splitmybill.ai_services.llm import LLMProviderFactory
from splitmybill.data_model.split import LLMSplitResponse
from splitmybill.interface.base import BaseInterface
from splitmybill.parser.llm import AnthropicParser

if TYPE_CHECKING:
    from telegram import Update

    from splitmybill.data_model.split import BillSplitModel

# Define conversation states
(COLLECTING_PARTICIPANTS,
 WAITING_FOR_RECEIPT,
 COLLECTING_INSTRUCTIONS) = range(3)


class TelegramSplitter(BaseInterface):
    """Telegram interface for bill splitting using LLM."""

    SYSTEM_PROMPT = """You are an AI assistant that helps split bills between people.

Your task is:
1. Review the receipt items and participant list provided
2. Understand the natural language splitting instructions
3. Create a BillSplitModel with:
   - Common items (split equally among all participants)
   - Separate items (split between specific participants)
4. If any items aren't clearly addressed in the instructions, ask for clarification

Rules for splitting:
- Items must be either common (everyone) or separate (specific people)
- For separate items:
  * Create duplicate items for each participant sharing the item
  * Split the cost equally between participants
  * Example: A $20 pizza split between Alice and Bob creates:
    - Pizza (Alice's share) at $10
    - Pizza (Bob's share) at $10
- All items must be accounted for in the final split
- All splits must be mathematically correct and total to the receipt amount

Remember:
- Ask for clarification if any item's split is unclear
- Return a complete response only when all items have clear split instructions
- Maintain context from previous clarifications in the conversation"""
    def __init__(
            self,
            token: str,
            model_name: str = "anthropic/claude-3-5-sonnet-20241022",
            api_key: str | None = None,
            **kwargs
    ):
        self.application = Application.builder().token(token).build()
        self.llm = LLMProviderFactory.create_provider(
            model_name=model_name,
            output_data_model=LLMSplitResponse,
            api_key=api_key,
            keep_history=True
        )
        self.api_key = api_key
        self.model_name = model_name

        # Set up conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                COLLECTING_PARTICIPANTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_participant),
                    CommandHandler("done", self.finish_participants)
                ],
                WAITING_FOR_RECEIPT: [
                    MessageHandler(filters.PHOTO, self.handle_receipt_photo)
                ],
                COLLECTING_INSTRUCTIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_split)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        self.application.add_handler(conv_handler)


    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the conversation and initialize user data."""
        context.user_data['participants'] = []
        await update.message.reply_text(
            "Let's split a bill! Please enter participant names one by one.\n"
            "Send /done when you've added all participants."
        )
        return COLLECTING_PARTICIPANTS

    async def handle_participant(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle incoming participant names."""
        name = update.message.text.strip()
        participants = context.user_data.get('participants', [])

        if name in participants:
            await update.message.reply_text(f"Error: {name} is already added")
            return COLLECTING_PARTICIPANTS

        participants.append(name)
        context.user_data['participants'] = participants
        await update.message.reply_text(
            f"Added {name}. Current participants: {', '.join(participants)}\n"
            "Add another participant or send /done when finished."
        )
        return COLLECTING_PARTICIPANTS

    async def finish_participants(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Finish collecting participants and move to receipt collection."""
        participants = context.user_data.get('participants', [])
        
        if len(participants) < 2:
            await update.message.reply_text("Error: At least 2 participants are required")
            return COLLECTING_PARTICIPANTS

        await update.message.reply_text(
            "Great! Now please send a photo of the receipt."
        )
        return WAITING_FOR_RECEIPT

    async def handle_receipt_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        photo = update.message.photo[-1]  # Get the largest photo
        file = await context.bot.get_file(photo.file_id)
        # Create temp file with correct extension
        mime_type = Path(file.file_path).suffix
        if mime_type not in AnthropicParser.MIME_TYPES:
            await update.message.reply_text(
                f"Unsupported image format {mime_type}. Supported formats are: "
                f"{', '.join(AnthropicParser.MIME_TYPES.keys())}"
            )
            return WAITING_FOR_RECEIPT

        with tempfile.NamedTemporaryFile(
            suffix=mime_type,
            delete=False,
            mode="w+"
        ) as tmp_file:
            await file.download_to_drive(tmp_file.name)
            print(tmp_file.name)
            try:
                parser = AnthropicParser(
                    Path(tmp_file.name),
                    model_name=self.model_name,
                    api_key=self.api_key
                )
                receipt_data = parser.extract_bill()
                context.user_data['receipt_data'] = receipt_data

                await update.message.reply_text(
                    "Please describe how you want to split the bill. You can use natural language.\n"
                    "For example:\n"
                    "- 'Split everything equally between all participants'\n"
                    "- 'Alice and Bob share the pizza, everyone splits the appetizers'\n"
                    "- 'The coffee is just for Charlie, split everything else equally'"
                )
                return COLLECTING_INSTRUCTIONS

            except Exception as e:
                print(e)
                await update.message.reply_text(
                    f"Error processing receipt: {str(e)}\n"
                    "Please try uploading the image again."
                )
                return WAITING_FOR_RECEIPT
            finally:
                Path(tmp_file.name).unlink(missing_ok=True)


    async def handle_split_instructions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle splitting instructions and generate split."""
        instructions = update.message.text.strip()
        receipt_data = context.user_data.get('receipt_data')
        
        # Initialize chat history if not already done
        if 'chat_initialized' not in context.user_data:
            self.llm.history = [
                ("system", self.SYSTEM_PROMPT),
                ("human", (
                    "Here is the receipt and participant information:\n"
                    f"Receipt: {receipt_data.model_dump()}\n"
                    f"Participants: {context.user_data['participants']}"
                ))
            ]
            context.user_data['chat_initialized'] = True

        response = self.llm.invoke(instructions)

        if response.is_complete:
            split_result = response.split_result
            split_result.calculate_shares(receipt_data)
            
            # Display results using prettytable
            result_text = self._format_split_results(split_result)
            await update.message.reply_text(result_text)
            return ConversationHandler.END
        else:
            await update.message.reply_text(response.clarification_question)
            return COLLECTING_INSTRUCTIONS
    
    async def collect_split(  # type: ignore
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle splitting instructions and generate split."""
        instructions = update.message.text.strip()
        receipt_data = context.user_data.get('receipt_data')
        
        if 'chat_initialized' not in context.user_data:
            self.llm.history = [
                ("system", self.SYSTEM_PROMPT),
                ("human", (
                    "Here is the receipt and participant information:\n"
                    f"Receipt: {receipt_data.model_dump()}\n"
                    f"Participants: {context.user_data['participants']}"
                ))
            ]
            context.user_data['chat_initialized'] = True

        response = self.llm.invoke(instructions)

        if response.is_complete:
            split_result = response.split_result
            split_result.calculate_shares(receipt_data)
            
            await self.display_split(update, context, split_result)
            return ConversationHandler.END
        else:
            await update.message.reply_text(response.clarification_question)
            return COLLECTING_INSTRUCTIONS

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        await update.message.reply_text("Bill splitting cancelled.")
        return ConversationHandler.END

    def run(self):
        """Start the bot."""
        self.application.run_polling()

    # Required interface methods
    async def display_split(  # type: ignore
            self,
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            split_data: BillSplitModel
    ) -> None:
        """Display split results in Telegram message."""
        messages = []

        # Common Items Table
        if split_data.common_items:
            table = PrettyTable()
            table.set_style(TableStyle.MARKDOWN)
            table.field_names = ["Common Items", "Price", "Per Person"]
            per_person = len(split_data.participants)

            for item in split_data.common_items:
                table.add_row([
                    item.name,
                    f"${item.subtotal:.2f}",
                    f"${(item.subtotal / per_person):.2f}"
                ])
            messages.append("COMMON ITEMS:\n```\n" + str(table) + "\n```")

        # Separate Items Table
        if split_data.separate_items and any(split_data.separate_items.values()):
            table = PrettyTable()
            table.set_style(TableStyle.MARKDOWN)
            table.field_names = ["Separate Items", *split_data.participants]

            all_items = set()
            for items in split_data.separate_items.values():
                all_items.update(item.name for item in items)

            for item_name in sorted(all_items):
                row = [item_name]
                for person in split_data.participants:
                    amount = sum(
                        item.subtotal
                        for item in split_data.separate_items.get(person, [])
                        if item.name == item_name
                    )
                    row.append(f"${amount:.2f}")
                table.add_row(row)
            messages.append("SEPARATE ITEMS:\n```\n" + str(table) + "\n```")

        # Tax Breakdown Table
        table = PrettyTable()
        table.set_style(TableStyle.MARKDOWN)
        table.field_names = ["Person", "Pretax Amount", "Tax Share", "Total"]

        for person in split_data.participants:
            table.add_row([
                person,
                f"${split_data.participant_shares[person]:.2f}",
                f"${split_data.tax_shares[person]:.2f}",
                f"${split_data.total_shares[person]:.2f}"
            ])

        total_pretax = sum(split_data.participant_shares.values())
        total_tax = sum(split_data.tax_shares.values())
        total_final = sum(split_data.total_shares.values())

        table.add_row([
            "TOTAL",
            f"${total_pretax:.2f}",
            f"${total_tax:.2f}",
            f"${total_final:.2f}"
        ])
        messages.append("TAX BREAKDOWN:\n```\n" + str(table) + "\n```")

        # Send all tables as a single message with Markdown formatting
        await update.message.reply_text(
            "\n\n".join(messages),
            parse_mode='Markdown'
        )

        # Send final totals
        final_totals = ["FINAL TOTALS:"]
        for person in split_data.participants:
            total = split_data.total_shares[person]
            final_totals.append(f"{person}: ${total:.2f}")
        await update.message.reply_text("\n".join(final_totals))

