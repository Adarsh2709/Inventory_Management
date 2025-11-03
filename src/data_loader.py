from pathlib import Path
import pandas as pd
import re

def load_sales(csv_path: str):
    """
    Load and validate sales data from CSV or Excel file with flexible column names.
    
    The function tries to automatically detect and map common column name variations.
    
    Required data:
    - Date (or similar like 'Order Date', 'Transaction Date')
    - Product (or similar like 'Item', 'SKU', 'Product Name')
    - Quantity/Sales (or similar like 'Sold_Units', 'Units Sold', 'Qty')
    
    Optional:
    - Current_Stock (or similar like 'On Hand', 'Inventory', 'Stock')
    """
    try:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {csv_path}")
        
        # Read the file
        if str(path).lower().endswith('.csv'):
            df = pd.read_csv(path, parse_dates=True)
        else:  # Excel
            df = pd.read_excel(path, parse_dates=True)
        
        if df.empty:
            raise ValueError("The file is empty.")
        
        # Convert column names to lowercase for case-insensitive matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Common column name variations
        date_patterns = ['date', 'order date', 'sale date', 'transaction date', 'day']
        product_patterns = ['product', 'item', 'sku', 'product name', 'item name', 'product id']
        quantity_patterns = ['sold_units', 'quantity', 'units sold', 'sold', 'sales quantity', 'qty', 'units']
        stock_patterns = ['current_stock', 'stock', 'inventory', 'on hand', 'current inventory']
        
        # Function to find matching column
        def find_matching_column(patterns, df_columns):
            for pattern in patterns:
                for col in df_columns:
                    if re.search(pattern, col, re.IGNORECASE):
                        return col
            return None
        
        # Find matching columns
        date_col = find_matching_column(date_patterns, df.columns)
        product_col = find_matching_column(product_patterns, df.columns)
        quantity_col = find_matching_column(quantity_patterns, df.columns)
        stock_col = find_matching_column(stock_patterns, df.columns)
        
        # Check for required columns
        missing = []
        if not date_col:
            missing.append('date (or similar like Order Date, Transaction Date)')
        if not product_col:
            missing.append('product (or similar like Item, SKU, Product Name)')
        if not quantity_col:
            missing.append('quantity (or similar like Sold_Units, Units Sold, Qty)')
            
        if missing:
            raise ValueError("Could not find required columns: " + 
                          ", ".join(missing) + ".\n" +
                          "Please ensure your file contains date, product, and quantity information.")
        
        # Standardize column names
        df = df.rename(columns={
            date_col: 'date',
            product_col: 'product',
            quantity_col: 'sold_units'
        })
        
        if stock_col:
            df = df.rename(columns={stock_col: 'current_stock'})
        
        # Convert date column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].isnull().any():
            raise ValueError("Could not parse date column. Please ensure dates are in a standard format (e.g., YYYY-MM-DD).")
        
        # Convert quantity to numeric, replacing non-numeric values with 0 and logging a warning
        original_count = len(df)
        df['sold_units'] = pd.to_numeric(df['sold_units'], errors='coerce')
        
        # Count and report any non-numeric values
        null_count = df['sold_units'].isnull().sum()
        if null_count > 0:
            print(f"Warning: Found {null_count} non-numeric values in quantity column. These will be treated as 0.")
            df['sold_units'] = df['sold_units'].fillna(0)
        
        # Convert to integers (handles floats if any)
        df['sold_units'] = df['sold_units'].astype(int)
        
        # Check if all quantities are zero (which might indicate a parsing issue)
        if (df['sold_units'] == 0).all():
            print("Warning: All quantity values are zero. Please verify your quantity column contains valid numbers.")
        
        # Handle stock column
        if 'current_stock' in df.columns:
            df['current_stock'] = pd.to_numeric(df['current_stock'], errors='coerce').fillna(0).astype(int)
        else:
            df['current_stock'] = 0
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error loading file: {str(e)}")