import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import (
    Flask, render_template, request, send_file, 
    redirect, url_for, send_from_directory, flash, jsonify
)
import pandas as pd
import numpy as np
from data_loader import load_sales
from demand_engine import DemandEngine
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

# Initialize Flask app
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
           static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates/static'))
app.secret_key = 'your_secret_key_here'  # Change this in production

# Configure paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
TEMPLATE_DIR = BASE_DIR / 'templates'
UPLOAD_FOLDER = DATA_DIR / 'uploads'

# Create necessary directories
for directory in [DATA_DIR, OUTPUT_DIR, UPLOAD_FOLDER]:
    directory.mkdir(exist_ok=True, parents=True)

DEFAULT_DATA = UPLOAD_FOLDER / 'sample_data.csv'
OUTPUT_FILE = OUTPUT_DIR / 'restock_recommendations.csv'

# Sample data for demo purposes
SAMPLE_DATA = """Date,Product,Sold_Units,Current_Stock
2023-01-01,Product A,10,50
2023-01-02,Product A,15,40
2023-01-03,Product A,8,25
2023-01-04,Product A,12,17
2023-01-05,Product A,20,5
2023-01-01,Product B,5,30
2023-01-02,Product B,8,25
2023-01-03,Product B,12,17
2023-01-04,Product B,10,7
2023-01-05,Product B,15,0
"""

# Create sample data if it doesn't exist
if not os.path.exists(DEFAULT_DATA):
    with open(DEFAULT_DATA, 'w') as f:
        f.write(SAMPLE_DATA)

# Helper functions
def compute_metrics(df):
    """Compute inventory metrics for the dashboard"""
    # Make a copy to avoid modifying the original dataframe
    df = df.copy()
    
    # Standardize column names (in case load_sales didn't do it)
    df.columns = df.columns.str.lower().str.strip()
    
    # Map common column name variations to standard names
    column_map = {
        'date': 'date',
        'order date': 'date',
        'product': 'product',
        'item': 'product',
        'sku': 'product',
        'sold_units': 'sold_units',
        'quantity': 'sold_units',
        'qty': 'sold_units',
        'current_stock': 'current_stock',
        'stock': 'current_stock',
        'inventory': 'current_stock'
    }
    
    # Apply column name mapping
    df = df.rename(columns={col: new_col for col, new_col in column_map.items() 
                          if col in df.columns and new_col not in df.columns})
    
    # Ensure required columns exist
    missing_columns = []
    if 'product' not in df.columns:
        missing_columns.append('product (or item, sku)')
    if 'sold_units' not in df.columns:
        missing_columns.append('sold_units (or quantity, qty)')
    if missing_columns:
        raise ValueError(f"Could not find required columns: {', '.join(missing_columns)}. "
                        f"Available columns: {', '.join(df.columns)}")
    
    # Ensure we have a date column, if not create a dummy one
    if 'date' not in df.columns:
        df['date'] = pd.to_datetime('today')
    
    # Ensure we have a current_stock column, if not set to 0
    if 'current_stock' not in df.columns:
        df['current_stock'] = 0
    
    # Group by product and calculate metrics
    metrics = []
    for product, group in df.groupby('product'):
        try:
            # Basic metrics
            avg_demand = group['sold_units'].mean()
            std_demand = group['sold_units'].std() if len(group) > 1 else 0
            current_stock = group['current_stock'].iloc[0] if 'current_stock' in group.columns else 0
            
            # Calculate safety stock (1.65 z-score for 95% service level)
            lead_time_days = 7  # Default lead time
            safety_stock = 1.65 * std_demand * np.sqrt(lead_time_days) if not np.isnan(std_demand) else 0
            
            # Calculate reorder point
            reorder_point = (avg_demand * lead_time_days) + safety_stock
            
            # Determine if reorder is needed
            needs_reorder = current_stock <= reorder_point
            
            # Calculate inventory turnover (annual)
            days_of_inventory = current_stock / avg_demand if avg_demand > 0 else 0
            inventory_turnover = 365 / days_of_inventory if days_of_inventory > 0 else 0
            
            # Check for potential stockout
            days_until_stockout = current_stock / avg_demand if avg_demand > 0 else float('inf')
            potential_stockout = days_until_stockout < lead_time_days * 1.5  # 1.5x lead time as buffer
            
            metrics.append({
                'product': str(product),  # Ensure product is string
                'current_stock': int(current_stock),
                'avg_demand': round(avg_demand, 2),
                'safety_stock': round(safety_stock, 2),
                'reorder_point': round(reorder_point, 2),
                'inventory_turnover': round(inventory_turnover, 2),
                'needs_reorder': needs_reorder,
                'potential_stockout': potential_stockout,
                'days_until_stockout': round(days_until_stockout, 1) if not np.isinf(days_until_stockout) else float('inf')
            })
        except Exception as e:
            print(f"Error processing product {product}: {str(e)}")
            continue
    
    if not metrics:
        raise ValueError("No valid products found in the data. Please check your file format.")
    
    return pd.DataFrame(metrics)

def generate_demand_plot(df, product):
    """Generate a demand plot for a specific product"""
    try:
        plt.figure(figsize=(10, 6))
        
        # Standardize column names
        df = df.copy()
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column name variations
        column_map = {
            'date': 'date',
            'order date': 'date',
            'product': 'product',
            'item': 'product',
            'sku': 'product',
            'sold_units': 'sold_units',
            'quantity': 'sold_units',
            'qty': 'sold_units',
            'current_stock': 'current_stock',
            'stock': 'current_stock',
            'inventory': 'current_stock'
        }
        
        # Apply column name mapping
        df = df.rename(columns={col: new_col for col, new_col in column_map.items() 
                              if col in df.columns and new_col not in df.columns})
        
        # Ensure required columns exist
        if 'product' not in df.columns or 'sold_units' not in df.columns:
            raise ValueError("Missing required columns for plotting")
            
        # Ensure we have a date column, if not create a dummy one
        if 'date' not in df.columns:
            df['date'] = pd.to_datetime('today')
        
        # Filter data for the specific product
        product_data = df[df['product'].astype(str).str.lower() == str(product).lower()].copy()
        
        if product_data.empty:
            raise ValueError(f"No data found for product: {product}")
        
        # Sort by date to ensure proper line plotting
        product_data = product_data.sort_values('date')
        
        # Create the plot
        plt.plot(product_data['date'], product_data['sold_units'], marker='o', label='Daily Sales')
        
        # Add average line
        avg_sales = product_data['sold_units'].mean()
        plt.axhline(y=avg_sales, color='r', linestyle='--', label=f'Avg: {avg_sales:.1f} units/day')
        
        # Add current stock if available
        if 'current_stock' in product_data.columns:
            current_stock = product_data['current_stock'].iloc[0]
            plt.axhline(y=current_stock, color='g', linestyle=':', 
                       label=f'Current Stock: {current_stock}')
        
        # Customize the plot
        plt.title(f'Sales Trend - {product}')
        plt.xlabel('Date')
        plt.ylabel('Units Sold')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        # Save plot to a bytes buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        
        # Convert to base64 for embedding in HTML
        plot_data = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{plot_data}"
        
    except Exception as e:
        print(f"Error generating plot for {product}: {str(e)}")
        # Return a transparent 1x1 pixel as fallback
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    """Render the main page with file upload form and handle file uploads"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected. Please choose a file to upload.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'error')
            return redirect(request.url)
        
        # Check file extension
        if not (file.filename.lower().endswith('.csv') or file.filename.lower().endswith(('.xls', '.xlsx'))):
            flash('Unsupported file format. Please upload a CSV or Excel file.', 'error')
            return redirect(request.url)
        
        try:
            # Save the uploaded file
            file_ext = os.path.splitext(file.filename)[1].lower()
            filename = f"upload_{int(datetime.now().timestamp())}{file_ext}"
            filepath = UPLOAD_FOLDER / filename
            file.save(filepath)
            
            # Process the file
            try:
                df = load_sales(str(filepath))
                
                # Check if we have any data
                if len(df) == 0:
                    flash('The uploaded file appears to be empty or contains no valid data.', 'error')
                    return redirect(url_for('index'))
                
                # Save a copy as the active dataset
                df.to_csv(DEFAULT_DATA, index=False)
                
                flash('File successfully uploaded and processed', 'success')
                return redirect(url_for('dashboard'))
                
            except ValueError as ve:
                # More user-friendly error messages
                error_msg = str(ve)
                if 'Could not find required columns' in error_msg:
                    flash(f'File format issue: {error_msg}', 'error')
                elif 'Could not parse date column' in error_msg:
                    flash('Date format issue: Please ensure your date column is in a standard format (e.g., YYYY-MM-DD).', 'error')
                else:
                    flash(f'Error processing file: {error_msg}', 'error')
                return redirect(url_for('index'))
                
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and process the data"""
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)
    
    if file:
        try:
            # Save the uploaded file
            filename = f"upload_{int(datetime.now().timestamp())}.csv"
            filepath = UPLOAD_FOLDER / filename
            file.save(filepath)
            
            # Process the file
            df = load_sales(str(filepath))
            
            # Save a copy as the active dataset
            df.to_csv(DEFAULT_DATA, index=False)
            
            flash('File successfully uploaded and processed', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Render the main dashboard with inventory metrics"""
    try:
        # Load and process the data
        df = load_sales(str(DEFAULT_DATA))
        
        # Standardize column names for the dashboard
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column name variations
        column_map = {
            'date': 'date',
            'order date': 'date',
            'product': 'product',
            'item': 'product',
            'sku': 'product',
            'sold_units': 'sold_units',
            'quantity': 'sold_units',
            'qty': 'sold_units',
            'current_stock': 'current_stock',
            'stock': 'current_stock',
            'inventory': 'current_stock'
        }
        
        # Apply column name mapping
        df = df.rename(columns={col: new_col for col, new_col in column_map.items() 
                              if col in df.columns and new_col not in df.columns})
        
        # Compute metrics
        metrics = compute_metrics(df)
        
        # Generate plots for each product
        plots = {}
        if 'product' in df.columns:
            for product in df['product'].unique():
                plots[product] = generate_demand_plot(df, product)
        
        # Save metrics to CSV
        metrics.to_csv(OUTPUT_FILE, index=False)
        
        # Convert DataFrame to list of dicts for the template
        metrics_data = metrics.to_dict(orient='records')
        
        return render_template('dashboard.html', 
                             metrics=metrics_data,
                             plots=plots,
                             products=df['product'].unique().tolist() if 'product' in df.columns else [])
        
    except Exception as e:
        import traceback
        print(f"Error in dashboard: {str(e)}\n{traceback.format_exc()}")
        flash(f'Error loading data: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/metrics')
def api_metrics():
    """API endpoint to get metrics data"""
    try:
        df = load_sales(str(DEFAULT_DATA))
        
        # Standardize column names for the dashboard
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column name variations
        column_map = {
            'date': 'date',
            'order date': 'date',
            'product': 'product',
            'item': 'product',
            'sku': 'product',
            'sold_units': 'sold_units',
            'quantity': 'sold_units',
            'qty': 'sold_units',
            'current_stock': 'current_stock',
            'stock': 'current_stock',
            'inventory': 'current_stock'
        }
        
        # Apply column name mapping
        df = df.rename(columns={col: new_col for col, new_col in column_map.items() 
                              if col in df.columns and new_col not in df.columns})
        
        metrics = compute_metrics(df)
        return jsonify(metrics.to_dict(orient='records'))
    except Exception as e:
        import traceback
        print(f"Error in api_metrics: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/plot/<product>')
def api_plot_demand(product):
    """API endpoint to get demand plot for a product"""
    try:
        df = load_sales(str(DEFAULT_DATA))
        
        # Standardize column names for the dashboard
        df.columns = df.columns.str.lower().str.strip()
        
        # Map common column name variations
        column_map = {
            'date': 'date',
            'order date': 'date',
            'product': 'product',
            'item': 'product',
            'sku': 'product',
            'sold_units': 'sold_units',
            'quantity': 'sold_units',
            'qty': 'sold_units',
            'current_stock': 'current_stock',
            'stock': 'current_stock',
            'inventory': 'current_stock'
        }
        
        # Apply column name mapping
        df = df.rename(columns={col: new_col for col, new_col in column_map.items() 
                              if col in df.columns and new_col not in df.columns})
        
        plot_data = generate_demand_plot(df, product)
        return jsonify({'plot': plot_data})
    except Exception as e:
        import traceback
        print(f"Error in api_plot_demand: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    """Download the recommendations as CSV"""
    if OUTPUT_FILE.exists():
        return send_file(
            OUTPUT_FILE,
            as_attachment=True,
            download_name=f'inventory_recommendations_{datetime.now().strftime("%Y%m%d")}.csv',
            mimetype='text/csv'
        )
    flash('No recommendations available to download', 'error')
    return redirect(url_for('dashboard'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Enable more detailed error reporting
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_EXTENSIONS'] = ['.csv', '.xlsx']
    app.config['DEBUG'] = True
    
    # Add request logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Try multiple ports if needed (avoiding common ports)
    ports = [5055, 5056, 5057, 5058, 5059]
    
    for port in ports:
        try:
            print(f"\nAttempting to start server on port {port}...")
            app.run(debug=True, host='127.0.0.1', port=port, use_reloader=False)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"Port {port} is in use, trying next port...")
                continue
            print(f"Error starting server on port {port}: {e}")
            raise
    else:
        print("\nFailed to start server. All ports are in use or inaccessible.")
        print("Please close any other applications using these ports and try again.")