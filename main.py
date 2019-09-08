import pymysql
from app import app
from db_config import mysql
from flask import jsonify
from flask import flash, request
import datetime

# This webservice adds new customer to the customerdata base. A json object with customer name and working
# hours is accepted and the logic calculates the intersection of buisness hours of the vendor and the customer
# so that the mesaages can be sent during customer's working hours only.


@app.route('/addcustomer', methods=['POST'])
def add_user():
    #business_hours are stored as dictionary object as of now for demo and POC as it is a single entity object.
    business_hours = {'start_at':'11:00:00','end_at':'21:00:00'}
    conn = mysql.connect()
    cursor = conn.cursor()
    try:
        _json = request.json
        _name = _json['name']
        _email = _json['email']
        _contact = _json['contact']
        _startat = _json['startat']
        _endat = _json['endat']

        if (datetime.datetime.strptime(_startat,'%H:%M:%S').time()) <= (datetime.datetime.strptime(business_hours['start_at'],'%H:%M:%S').time()):
            _msgstarttim = datetime.datetime.strptime(business_hours['start_at'],'%H:%M:%S').time()
            _msgstarttim = str(_msgstarttim)
        else:
            _msgstarttim = datetime.datetime.strptime(_startat,'%H:%M:%S').time()
            _msgstarttim = str(_msgstarttim)

        
        if (datetime.datetime.strptime(_endat,'%H:%M:%S').time()) <= (datetime.datetime.strptime(business_hours['end_at'],'%H:%M:%S').time()):
            _msgendtim = datetime.datetime.strptime(_endat,'%H:%M:%S').time()
            _msgendtim = str(_msgendtim)
        else:
            _msgendtim = datetime.datetime.strptime(business_hours['end_at'],'%H:%M:%S').time()
            _msgendtim = str(_msgendtim)

        
        if request.method == 'POST':
            sql = ("INSERT INTO CUSTOMER_DATA_2(name,email,contact,start_at,end_at,msg_hr_st,msg_hr_end) VALUES(%s,%s,%s,%s,%s,%s,%s)")
            data = (_name,_email,_contact,_startat,_endat,_msgstarttim,_msgendtim)
            print(data)
           
            cursor.execute(sql, data)
            conn.commit()
            resp = jsonify('customer added successfully!')
            resp.status_code = 200
            return resp
        else:
            return not_found()
    except Exception as e:
        print(e)
        print(cursor._last_executed)
    finally:
        cursor.close() 
        conn.close()


@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404
    return resp

# This webservice handles outgoing services for the business. It accepts a json object having the message which has to be sent
# to customers. In case the payload is accepted on a normal working day, the message is delivered to those customers who are
# active during that time.In case a customer is unable to receive a message, the message is saved to a message_queue database
# with details including customer name, the actual text message and the time at which the message can be sent to the customer 
# on the following day. In case the payload is received on a weekend, response is sent back accordingly

@app.route('/outgoings',methods=['POST'])
def send_message():
    current_time = datetime.datetime.now().time()
    today = datetime.datetime.now().strftime("%A")
   
    
    print(type(current_time))
    print(type(today))
    conn = mysql.connect()
    cursor = conn.cursor()
    try:
        json = request.json
        message = json['message']
        print(message)
        message_queue = []
        message_pend_queue = []

        if request.method == 'POST' and str(today) not in ['Saturday', 'Sunday']:
        # if request.method == 'POST':    
            sql_transact = "select * from CUSTOMER_DATA_2"
            cursor.execute(sql_transact)
            for data in cursor.fetchall():
                if (current_time > datetime.datetime.strptime(data[6],'%H:%M:%S').time()) and (current_time < datetime.datetime.strptime(data[7],'%H:%M:%S').time()):
                    token = {
                        'customername' : data[1],
                        'customeremail' : data[2],
                        'message' : message
                        }
                    message_queue.append(token)
                    
                    
                else:
                    # token = {
                    #     'customername' : data[1],
                    #     'customeremail' : data[2],
                    #     'time' : data[4],
                    #     'message' : message
                    # }
                    message_pend_queue = (data[1],data[2],data[4],message)
                    add_to_message_queue(message_pend_queue)

            resp_final = jsonify(message_queue)
            resp_final.status_code = 200
            return resp_final 

        elif str(today) in ['Saturday','Sunday']:
            
            token = [{
                'message' : 'Marketing communications are not functional on weekends. Your messages will be stored to weekend message queue database and sent on next working day'
            }]
            print(token)
            return jsonify(token) 

        else:
            return not_found()        

    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

# This service handles response to incoming messages from the customer's end. It receives a payload with order details including
# customer name, order id, product id and payment details. In case the order is placed during normal working hours; confirmation is send
# to the customer at the same time. In case the order is placed outside the normal working hours, the order details are
# moved to pending order table and customer is informed that the order will be processed next day.
# In case the order is received on weekends; the customer is informed that the order will be processed on Monday and
# the order details are moved to pending_order database.

@app.route('/incomings',methods=['POST'])
def incomings():
    today = datetime.datetime.now().strftime("%A")
    #today = 'Monday'
    business_hours = {'start_at':'11:00:00','end_at':'21:00:00'}
    current_time = datetime.datetime.now().time()
    print(type(today))

    try:
        json = request.json
        customer_name = json['cust_name']
        order_id = json['order_id']
        product_id = json['product_id']
        payment_stat = json['payment_stat']


        if request.method == 'POST':
            if today in ['Saturday', 'Sunday']:
                
                token = [{
                    'customer_name': customer_name,
                    'message' : 'Hi '+customer_name+', we have received order and payment has been received through NEFT. Shipping will be done on next working day.'
                }]
                
                if today == 'Saturday':
                    order_process_date = datetime.datetime.today() + datetime.timedelta(days=2)
                    order_process_date = order_process_date.strftime("%m/%d/%Y")
                elif today == 'Sunday':
                    order_process_date = datetime.datetime.today() + datetime.timedelta(days=1)
                    order_process_date = order_process_date.strftime("%m/%d/%Y")
                else:
                    order_process_date = datetime.datetime.today()
                    order_process_date = order_process_date.strftime("%m/%d/%Y")

                add_pendingorder_data(customer_name,order_id,product_id,payment_stat,order_process_date)
                return jsonify(token)
            else:
                if (current_time > datetime.datetime.strptime(business_hours['start_at'],'%H:%M:%S').time()) and (current_time < datetime.datetime.strptime(business_hours['end_at'],'%H:%M:%S').time()):
                    token = [{
                        'customer_name' : customer_name,
                        'message' : 'Order With order ID' + order_id + 'processed sucessfully'
                    }]
                    return jsonify(token)
                else:
                    token = [{
                        'customer_name' : customer_name,
                        'message' : 'Order With order ID' + order_id + 'is received outside working hours; will be processed on next working day'
                    }]
                    order_process_date = datetime.datetime.today() + datetime.timedelta(days=1)
                    order_process_date = order_process_date.strftime("%m/%d/%Y")
                    add_pendingorder_data(customer_name,order_id,product_id,payment_stat,order_process_date)
                    return jsonify(token)





    except Exception as e:
        print(e)

# This method saves data on the pending orders which are placed outside the working hours of the business.

def add_pendingorder_data(customer_name,order_id,product_id,payment_stat,order_process_date):
    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        sql = ("INSERT INTO PENDING_ORDER_2(cust_name,order_id,product_id,payment_stat,order_process_date) VALUES(%s,%s,%s,%s,%s)")
        data = (customer_name,order_id,product_id,payment_stat,order_process_date) 
        cursor.execute(sql, data)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

# This method stores the details of marketing messaged which could not be sent to certail customers on a certain day
# as the payload was received outside their working hours. These messaged can be sent through scheduled python webservice
# which will find new messaged which are remaining to be sent to the customers and delete the same after they are sent.        

def add_to_message_queue(message_pend_queue):
    conn = mysql.connect()
    cursor = conn.cursor()

    try:
        sql = ("INSERT INTO PENDING_messages(cust_name,cust_email,msg_time,message) VALUES(%s,%s,%s,%s)")
        data = message_pend_queue
        cursor.execute(sql,data)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run()
		