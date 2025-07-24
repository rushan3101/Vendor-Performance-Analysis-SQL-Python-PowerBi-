#Importing Libraries
import pandas as pd
import time
import sqlite3
import logging
from ingest_db import ingest_db

#Configuring logging
logging.basicConfig(
    filename='logs/get_vendor_summary.log',
    level= logging.DEBUG,
    format = "%(asctime)s — %(levelname)s — %(message)s",
    filemode = "a"
)

def create_vendor_summary(conn) :
    '''This function will merge all the tables to get the overall vendor summary and add new columns in the resultant data'''
    start=time.time()
    vendor_sales_summary = pd.read_sql_query("""
    WITH PurchaseSummary AS (
        SELECT
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.PurchasePrice,
            p.Store,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        WHERE p.PurchasePrice > 0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.PurchasePrice, p.Store
    ),
    
    StoreCity AS (
        SELECT DISTINCT Store, City FROM begin_inventory WHERE City is NOT NULL
        UNION
        SELECT DISTINCT Store, City FROM end_inventory WHERE City is NOT NULL
    ),
    
    SalesSummary AS (
        SELECT
            s.VendorNo,
            s.VendorName,
            s.Brand,
            s.Store,
            SUM(s.SalesPrice * s.SalesQuantity) * 1.0 / SUM(s.SalesQuantity) AS AvgSalesPrice,
            SUM(s.SalesQuantity) AS TotalSalesQuantity,
            SUM(s.SalesDollars) AS TotalSalesDollars,
            SUM(s.ExciseTax) AS TotalExciseTax
        FROM sales s
        GROUP BY s.VendorNo, s.VendorName, s.Brand, s.Store
    ),
    
    FreightSummary AS (
        SELECT
            vi.VendorNumber,
            SUM(vi.Freight) AS TotalFreightCost
        FROM vendor_invoice vi
        GROUP BY vi.VendorNumber
    )
    
    SELECT 
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        fs.TotalFreightCost,
        ps.Store,
        sc.City,
        ss.AvgSalesPrice,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalExciseTax
    FROM PurchaseSummary ps
    LEFT JOIN StoreCity sc ON ps.Store = sc.Store
    LEFT JOIN SalesSummary ss ON ps.VendorNumber = ss.VendorNo AND ps.Brand = ss.Brand AND ps.Store = ss.Store
    LEFT JOIN FreightSummary fs ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.VendorNumber
    """, conn)
    
    end = time.time()
    time_taken = (end - start) / 60
    return vendor_sales_summary, time_taken


def clean_data(vendor_sales_summary) :
    '''This function will clean the data'''
    
    #Filling null values with 0
    vendor_sales_summary.fillna(0,inplace=True)

    #Rounding Average Sales price to two decimal place
    vendor_sales_summary["AvgSalesPrice"] = vendor_sales_summary.AvgSalesPrice.map(lambda x : round(x,2))

    #Changing TotalSalesQuantity datatype to int
    vendor_sales_summary["TotalSalesQuantity"] = vendor_sales_summary.TotalSalesQuantity.astype(int)

    #Removing whitespaces in vendor names and Description
    vendor_sales_summary["VendorName"] = vendor_sales_summary.VendorName.str.strip()
    vendor_sales_summary["Description"] = vendor_sales_summary.Description.str.strip()

    #Creating new columns for better analysis
    vendor_sales_summary["GrossProfit"] = ( vendor_sales_summary.AvgSalesPrice - vendor_sales_summary.PurchasePrice )*vendor_sales_summary.TotalSalesQuantity
    vendor_sales_summary["GrossProfitMargin"] = np.where(vendor_sales_summary.TotalSalesDollars == 0, 0,\
                                            (vendor_sales_summary.GrossProfit/vendor_sales_summary.TotalSalesDollars)*100 )
    vendor_sales_summary["StockTurnover"] = np.where(vendor_sales_summary.TotalPurchaseQuantity == 0, 0,\
                                            vendor_sales_summary.TotalSalesQuantity/vendor_sales_summary.TotalPurchaseQuantity )
    vendor_sales_summary["SalesToPurchaseRatio"] = np.where(vendor_sales_summary.TotalPurchaseDollars == 0, 0,\
                                            vendor_sales_summary.TotalSalesDollars/vendor_sales_summary.TotalPurchaseDollars )

    return vendor_sales_summary

if __name__ == "__main__" :

    #Creating connection
    conn = sqlite3.connect("inventory.db")

    logging.info("Creating Vendor Summary Table....")
    summary_df,time_taken = create_vendor_summary(conn)
    logging.info(summary_df)
    logging.info(f'Time Taken : {time_taken}')

    logging.info("Cleaning Data....")
    clean_df = clean_data(summary_df)
    logging.info(clean_df)

    logging.info("Ingesting Data....")
    ingest_db(clean_df,"vendor_summary_data",conn)
    logging.info("Completed")
    
    