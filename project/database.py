import mysql.connector

def get_connection():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sravanthi@33",
        database="her_market"
    )

    return conn