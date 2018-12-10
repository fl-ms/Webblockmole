## Updatet die new_tx flag des Bitcoinadressobjekts in der SQLite DB, wenn neue TX vorhanden sind. 

# Hintergrundprozess

import sqlite3
import time
import requests
from datetime import datetime
from blockchain import blockexplorer


class BitcoinAddress:
    """
    In dieser Klasse werden alle relevanten Daten zur Bitcoinadresse gespeichert 
    """
    def __init__(self, db_id, address, n_tx, total_received, total_sent, balance, last_tx_date, data_created_date, comment, user_id, new_tx=False):
        
        self.address = address
        self.n_tx = n_tx
        self.total_received = total_received
        self.total_sent = total_sent
        self.balance = balance
        self.last_tx_date = last_tx_date
        self.data_created_date = 0
        self.comment = comment
        self.db_id = db_id
        self.user_id = user_id
    
    def check_for_update(self):
        api_address = blockexplorer.get_address(self.address)
        api_transactions = api_address.transactions
        if self.n_tx < api_address.n_tx:
            self.total_received = api_address.total_received
            self.total_sent = api_address.total_sent
            self.balance = api_address.final_balance
            self.n_tx = api_address.n_tx
            self.last_tx_date = api_transactions[0].time
            return True
        else:
            return False

    def to_list(self):
        list = []
        list.append(self.db_id)
        list.append(self.address)
        list.append(self.n_tx)
        list.append(self.total_received)
        list.append(self.total_sent)
        list.append(self.last_tx_date)
        list.append(self.data_created_date)
        list.append(self.balance)
        list.append(str(self.comment))
        return list

def case_load_into_object():
    # Loads SQLite data into a list of python objects
    connect = sqlite3.connect("app.db")
    cursor = connect.cursor()
    address_list = []
    cursor.execute("SELECT * FROM address" )

    for row in cursor:
        db_id = row[0]
        address = row[1]
        n_tx = row[2]
        total_received = row[3]
        total_sent = row[4]
        last_tx = row[5]
        date_added = row[6]
        balance = row[7]
        comment = row[8]
        user_id = row[9]
        final_object = BitcoinAddress(db_id, address, n_tx, total_received, total_sent, balance, last_tx, date_added, comment, user_id)
        address_list.append(final_object)
    
    connect.close()
    return address_list

def write_into_db(case_name, address_object, update=False, new_tx=0):
    # Writes all objects in address_list into SQLite
    connect = sqlite3.connect("app.db")
    cursor = connect.cursor()   

    t_rec = address_object.total_received / 100000000
    t_sen = address_object.total_sent / 100000000
    bal = address_object.balance / 100000000

    if update == False and new_tx == 0:
        liste = []
        liste.append(address_object.address)
        liste.append(address_object.n_tx)
        liste.append(address_object.total_received)
        liste.append(address_object.total_sent)        
        liste.append(datetime.fromtimestamp(address_object.last_tx_date).strftime('%Y-%m-%d %H:%M:%S'))
        liste.append(address_object.data_created_date)
        liste.append(address_object.balance)
        liste.append(address_object.comment)
        cursor.execute("""INSERT INTO [%s] VALUES (NULL,?,?,?,?,?,?,?,?,?)""" % case_name , liste)
    
    if update == True:
        cursor.execute("UPDATE '{}' SET n_tx = '{}', total_received = '{}', total_sent = '{}', last_tx = '{}', balance = '{}' WHERE id = '{}'".format(case_name, address_object.n_tx, t_rec, t_sen , datetime.fromtimestamp(address_object.last_tx_date).strftime('%Y-%m-%d %H:%M:%S'), bal, address_object.db_id))
    
    if new_tx == 1:
        cursor.execute("UPDATE '{}' SET new_tx = '{}' WHERE address_id = '{}'".format(case_name, 1, address_object.db_id))
    
    connect.commit()
    connect.close()

def main():
    while True:
        print("Initialisiere Update...")
        objekte = case_load_into_object()
        success = 0
        abort = 0
        checks = 0
        print("Lade API Daten...")
        for i in objekte:            
            try:
                checks += 1
                if i.check_for_update() == True:
                    
                    write_into_db("address", i, update=True)
                    write_into_db("followed_addresses", i, new_tx=1)
                    success += 1
                        
            except:
                abort += 1

        print("\nAbgeschlossen! Es wurden {} Daten gecheckt und neue Daten für {} Datensätze gefunden. Insgesamt gab es {} Timeouts...\n\nWarte 5 Minuten...\n\n#####################\n".format(checks, success, abort))
        time.sleep(30)
       
       
if __name__ == "__main__":
    main()