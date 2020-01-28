import telegram
import logging
from telegram import ReplyKeyboardMarkup , InlineKeyboardButton , InlineKeyboardMarkup , replykeyboardmarkup , ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters , CallbackQueryHandler , ConversationHandler
import bs4
import requests
import re
import sqlite3
from tabulate import tabulate

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

CODE, DETAILS, COUNT, BUTTON ,SaveuserDetails = range(5)
pcode = 0
counter = 0


connection = sqlite3.connect('userDetails.db',check_same_thread=False)

def start(update, context):
    reply_keyboard = [['خرید', 'مشاهده سبد خرید']]

    update.message.reply_text("""سلام {}
            این ربات فروشگاه زیورال است """.format(update.message.from_user.first_name),reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CODE

def selectProduct(code):
    print('select pro')
    search_Url = 'https://zivaral.ir/search?q='
    page = requests.get(search_Url+code)
    soup = bs4.BeautifulSoup(page.content,features="html.parser")
    if soup.find(class_= "styles__link___3hWDv")['href'] == 'NoneType':
        print('wrong code')
    product = soup.find(class_= "styles__link___3hWDv")['href']
    return(product)

def code(update, context):
    update.message.reply_text('لطفا نام محصول و یا کد محصول مورد نظر خود را وارد کنید',reply_markup=ReplyKeyboardRemove())
    return DETAILS

def show(update, context):
    user_id = str(update.message.from_user.id)
    labels=["نام : ","آدرس : ","شماره تماس : ","کد کالا :","تعداد :"]
    for row in connection.execute("select * from userdetails where user_id = ? ",(user_id,)):
        print(row)
        user_id, customer_name, address, phone_number ,pcode , count = row
        data=[customer_name, address, phone_number, pcode, count]
        table=zip(labels,data)
        #show_table =tabulate(table,tablefmt="fancy_grid")
        show_table =tabulate(table)
        context.bot.send_message(chat_id=update.message.chat_id,text= show_table)

    reply_keyboard = [['خرید', 'مشاهده سبد خرید']]

    update.message.reply_text('یکی از گزینه های زیر را انتخاب کنید',reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CODE

def details(update, context):
    global pcode
    print('page open')
    base_Url = 'https://zivaral.ir' 
    pcode = update.message.text     
    add = base_Url + selectProduct(pcode)
    page = requests.get(add)
    soup = bs4.BeautifulSoup(page.content, features="html.parser")
    imag = soup.find('img', {'src':re.compile('.jpg')})['src']
    context.bot.send_photo(chat_id= update.message.chat_id, photo= base_Url+imag)
    price_r = soup.find(class_="styles__final-price___1L1AM").text
    update.message.reply_text(price_r)
    detail = soup.find(class_= "styles__description___3dh1f").text
    update.message.reply_text(detail)

    kyeboard = [[InlineKeyboardButton('بله' , callback_data='yes'),InlineKeyboardButton('خیر' , callback_data='no')]]
    reply = InlineKeyboardMarkup(kyeboard)
    update.message.reply_text('آیا همین محصول مورد نظر شماست ؟', reply_markup = reply)

    return BUTTON

def button(update, context):
    query = update.callback_query
    if query.data == 'yes' :
        query.edit_message_text(text= 'لطفا تعداد مورد نیاز را وارد کنید')
        return COUNT
        
    elif query.data == 'no' :
        query.edit_message_text(text='لطفا کد محصول دیگری وارد کنید')
        return DETAILS


def count(update, context):
    global counter
    counter = update.message.text
    update.message.reply_text("""
             لطفا مشخصات خود را در قالب زیر وارد کنید
             اسم,آدرس,شماره تماس""")

    return SaveuserDetails

def database(user_id,customer_name,address,phone_number,pcode,count):
    print(user_id,customer_name,address,phone_number, pcode , count)
    connection.execute('''CREATE TABLE IF NOT EXISTS userdetails(user_id int,customer_name text,address text,phone_number int,pcode int,count int )''')
    connection.execute("INSERT INTO userdetails VALUES (?,?,?,?,?,?)",(user_id,customer_name,address,phone_number,pcode,count))
    connection.commit()

#Function to save user details in the database
def saveuserDetails(update , context):
    print('save user')
    global counter 
    user_id=update.message.from_user.id
    customer_name,address,phone_number=update.message.text.split(',')
    database(user_id,customer_name,address,phone_number,pcode,counter)
    #final msg
    update.message.reply_text(""" {}
             سفارش شما ثبت شد و در اولین فرصت به آن رسیدگی میشود""".format(update.message.from_user.first_name))
    show(update, context)         
                                                              

# def facts_to_str(user_data):
#     facts = list()

#     for key, value in user_data.items():
#         facts.append('{} - {}'.format(key, value))

#     return "\n".join(facts).join(['\n', '\n'])

def cancel(update, context):

    update.message.reply_text('به امید دیدار مجدد',reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("Token", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CODE: [MessageHandler(Filters.regex('^(خرید)$'),
                                      code),
                       MessageHandler(Filters.regex('^(مشاهده سبد خرید)$'),
                                      show)
                       ],

            DETAILS: [MessageHandler(Filters.text, details)],
            
            BUTTON: [CallbackQueryHandler(button)],

            COUNT: [MessageHandler(Filters.text, count)],

            SaveuserDetails:[MessageHandler(Filters.text, saveuserDetails)]

             },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()