# screenmagic



The explained approach is a small depiction of how customer and business message interchange can be handled with python microservices.
This approach consists of 3 rest APIs described below.

1.	/addcustomer: 
This webservice adds new customer to the customer database. A json object with customer name and working hours is accepted and the logic calculates the intersection of business hours of the vendor and the customer so that the messages can be sent during customer's working hours only.

2.	/outgoings: (to handle problem type 1 in problem statement)

This webservice handles outgoing services for the business. It accepts a json object having the message which must be sent to customers. In case the payload is accepted on a normal working day, the message is delivered to those customers who are active during that time. In case a customer is unable to receive a message, the message is saved to a message_queue database with details including customer name, the actual text message and the time at which the message can be sent to the customer on the following day. In case the payload is received on a weekend, response is sent back accordingly.

3.	/incomings: (handles problem type 2 in problem statement):

This service handles response to incoming messages from the customer's end. It receives a payload with order details including customer name, order id, product id and payment details. In case the order is placed during normal working hours; confirmation is send to the customer at the same time. In case the order is placed outside the normal working hours, the order details are moved to pending order table and customer is informed that the order will be processed next day. In case the order is received on weekends; the customer is informed that the order will be processed on Monday and the order details are moved to pending_order database.

Tecchnologies used:
1.	Python- Flask Framework
2.	MySQL database
3.	Postman for API-testing and Proof of concept development


