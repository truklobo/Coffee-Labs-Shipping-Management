# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
Chat Interface Views and API Endpoints
"""

# Flask modules
from flask import render_template, request, jsonify
from app import app, db_connection, cursor
import os

# Store conversation history in memory
conversation_history = {}

# ============================================================================
# MAIN ROUTES
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('shipping_home.html')

# ============================================================================
# CHAT INTERFACE & API ROUTES
# ============================================================================

@app.route('/chat')
def chat():
    """Render the chat interface page"""
    return render_template('shipping_chat.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat API requests using built-in Python only"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', 'default')
        
        # Get API endpoint, key, and model from headers or environment defaults
        api_endpoint = request.headers.get('X-API-Endpoint', os.getenv('API_ENDPOINT', 'https://llm-api.arc.vt.edu/api/v1/chat/completions'))
        api_key = request.headers.get('X-API-Key', os.getenv('API_KEY'))        model_name = request.headers.get('X-Model-Name', os.getenv('MODEL_NAME', 'gpt-oss-120b'))
        
        if not api_key:
            return jsonify({
                'error': 'No API key provided.',
                'message': 'Please set the X-API-Key header or configure a default key.'
            }), 401
        
        if conversation_id not in conversation_history:
            conversation_history[conversation_id] = []
        
        conversation_history[conversation_id].append({'role': 'user', 'content': user_message})
        context = get_business_context(user_message)
        response_text = generate_response(user_message, context, conversation_id, api_endpoint, api_key, model_name)
        
        if response_text:
            conversation_history[conversation_id].append({'role': 'assistant', 'content': response_text})
            return jsonify({'success': True, 'response': response_text, 'api_endpoint': api_endpoint, 'model': model_name}), 200
        else:
            return jsonify({'success': False, 'error': 'Could not generate a response'}), 500
    
    except Exception as e:
        app.logger.error(f"Chat API Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# CHAT HELPER FUNCTIONS
# ============================================================================

def build_table_from_orders(matches):
    """Build Bootstrap HTML table from order matches"""
    table_html = '''<div class="table-responsive">
<table class="table table-striped table-hover table-dark">
<thead>
<tr>
<th>Order ID</th>
<th>Supplier</th>
<th>Item</th>
<th>Quantity</th>
<th>Total</th>
<th>Date</th>
<th>Carrier</th>
</tr>
</thead>
<tbody>
'''
    
    for match in matches:
        order_id, supplier, item, qty, total, date, carrier = match
        # Truncate order ID for display
        short_id = order_id[:8] if len(order_id) > 8 else order_id
        carrier = carrier.strip() if carrier else 'N/A'
        
        # Format total as currency if not already formatted
        if not total.startswith('$'):
            try:
                total_float = float(total)
                total = f'${total_float:.2f}'
            except:
                total = f'${total}'
        
        table_html += f'''<tr>
<td>{short_id}</td>
<td>{supplier.strip()}</td>
<td>{item.strip()}</td>
<td>{qty}</td>
<td>{total}</td>
<td>{date}</td>
<td>{carrier}</td>
</tr>
'''
    
    table_html += '''</tbody>
</table>
</div>'''
    
    return table_html

def get_business_context(user_query):
    """
    Analyze user query, execute SQL, and return relevant data as context.
    This combines SQL query generation with data retrieval.
    """
    import re
    from datetime import datetime
    
    try:
        message_lower = user_query.lower()
        
        # Build SQL query based on user message
        base_query = """SELECT shipping_id, supplier_name, order_date, exp_delivery_date, 
                        actual_delivery_date, tracking_number, shipping_carrier, item_name, 
                        quantity, order_total, notes FROM Shipping"""
        where_clauses = []
        params = []
        order_by = " ORDER BY order_date DESC"
        limit = " LIMIT 50"
        
        # CARRIER filter (check this FIRST before supplier to avoid conflicts)
        carrier_keywords = ['fedex', 'ups', 'usps', 'dhl']
        carrier_found = False
        for carrier in carrier_keywords:
            if carrier in message_lower:
                where_clauses.append("UPPER(shipping_carrier) LIKE %s")
                params.append(f"%{carrier.upper()}%")
                carrier_found = True
                break
        
        # SUPPLIER filter (only if no carrier was found to avoid "shipped by DHL" being treated as supplier)
        if not carrier_found:
            supplier_match = re.search(r'(?:from|by|supplier)\s+(["\']?)([a-zA-Z0-9\s&]+)\1', message_lower, re.IGNORECASE)
            if supplier_match:
                supplier_name = supplier_match.group(2).strip()
                where_clauses.append("supplier_name LIKE %s")
                params.append(f"%{supplier_name}%")
        
        # ITEM filter
        item_match = re.search(r'(?:item|product)\s+(["\']?)([a-zA-Z0-9\s]+)\1', message_lower, re.IGNORECASE)
        if item_match:
            item_name = item_match.group(2).strip()
            where_clauses.append("item_name LIKE %s")
            params.append(f"%{item_name}%")
        
        # DATE RANGE filters
        date_range_match = re.search(r'(after|before|since)\s+([a-z]+)\s+(\d{1,2})', message_lower)
        if date_range_match:
            direction = date_range_match.group(1)
            month_str = date_range_match.group(2)
            day = date_range_match.group(3)
            
            month_map = {
                'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
                'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
                'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
                'august': '08', 'aug': '08', 'september': '09', 'sep': '09',
                'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
                'december': '12', 'dec': '12'
            }
            
            month_num = month_map.get(month_str[:3])
            if month_num:
                date_str = f"2025-{month_num}-{day.zfill(2)}"
                if direction in ['after', 'since']:
                    where_clauses.append("order_date > %s")
                else:  # before
                    where_clauses.append("order_date < %s")
                params.append(date_str)
        
        # SPECIFIC DATE
        specific_date_match = re.search(r'(?:on\s+)?([a-z]+)\s+(\d{1,2})(?:\s+|,\s*|\s*,)?(2025|2024)?', message_lower)
        if specific_date_match and not date_range_match:
            month_str = specific_date_match.group(1)
            day = specific_date_match.group(2)
            year = specific_date_match.group(3) or '2025'
            
            month_map = {
                'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
                'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
                'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
                'august': '08', 'aug': '08', 'september': '09', 'sep': '09',
                'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
                'december': '12', 'dec': '12'
            }
            
            month_num = month_map.get(month_str)
            if month_num:
                date_str = f"{year}-{month_num}-{day.zfill(2)}"
                where_clauses.append("order_date = %s")
                params.append(date_str)
        
        # SORTING
        if 'most expensive' in message_lower or 'highest' in message_lower:
            order_by = " ORDER BY order_total DESC"
            limit = " LIMIT 20"
        elif 'cheapest' in message_lower or 'lowest' in message_lower:
            order_by = " ORDER BY order_total ASC"
            limit = " LIMIT 20"
        elif 'recent' in message_lower or 'latest' in message_lower:
            order_by = " ORDER BY order_date DESC"
            limit = " LIMIT 30"
        elif 'oldest' in message_lower:
            order_by = " ORDER BY order_date ASC"
            limit = " LIMIT 20"
        
        # Build and execute query
        if where_clauses:
            sql_query = base_query + " WHERE " + " AND ".join(where_clauses) + order_by + limit
        else:
            sql_query = base_query + order_by + limit
        
        print(f"DEBUG: SQL Query: {sql_query}")
        print(f"DEBUG: Parameters: {params}")
        
        cursor.execute(sql_query, tuple(params))
        results = cursor.fetchall()
        
        print(f"DEBUG: Query returned {len(results)} results")
        
        # Get statistics
        cursor.execute("""SELECT COUNT(*) as total_orders, COUNT(DISTINCT supplier_name) as total_suppliers, 
                         COUNT(DISTINCT shipping_carrier) as total_carriers, SUM(order_total) as total_value 
                         FROM Shipping""")
        stats = cursor.fetchone()
        
        # Format context for LLM
        context = f"""DATABASE STATISTICS:
- Total Orders: {stats['total_orders'] if stats else 0}
- Total Suppliers: {stats['total_suppliers'] if stats else 0}
- Total Carriers: {stats['total_carriers'] if stats else 0}
- Total Value: ${stats['total_value'] if stats else 0}

QUERY RESULTS ({len(results)} matching orders):
"""
        
        # Add results in structured format
        for order in results:
            context += f"\nORDER|{order['shipping_id']}|{order['supplier_name']}|{order['item_name']}|{order['quantity']}|{order['order_total']}|{order['order_date']}|{order.get('shipping_carrier', 'N/A')}"
        
        if len(results) == 0:
            context += "\nNo orders found matching the criteria."
        
        return context
        
    except Exception as e:
        app.logger.error(f"Error getting context: {str(e)}")
        return "Database query failed. Unable to retrieve data."

def generate_response(user_message, context, conversation_id, api_endpoint='', api_key='', model_name='gpt-3.5-turbo'):
    """Generate response using external LLM API with database context"""
    import urllib.request
    import json
    
    print(f"DEBUG: generate_response called")
    print(f"DEBUG: API endpoint: {api_endpoint}")
    print(f"DEBUG: API key present: {bool(api_key)}")
    print(f"DEBUG: Model: {model_name}")
    
    try:
        # Prepare system message with database context
        system_message = f"""You are a helpful Business Intelligence Assistant for a shipping database.

Use the database results below to answer the user's question naturally and conversationally.

DATABASE RESULTS:
{context}

INSTRUCTIONS:
- Answer questions directly (e.g., "There are 150 total orders in the database")
- For queries asking to show/list/display data, create a Bootstrap HTML table
- For simple questions (how many, what's the total, etc.), give a text answer
- Be concise and accurate

TABLE FORMAT (when showing data):
<div class="table-responsive">
<table class="table table-striped table-hover table-dark">
<thead>
<tr>
<th>Order ID</th>
<th>Supplier</th>
<th>Item</th>
<th>Quantity</th>
<th>Total</th>
<th>Date</th>
<th>Carrier</th>
</tr>
</thead>
<tbody>
[rows here]
</tbody>
</table>
</div>"""

        # Build conversation messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        print(f"DEBUG: Building API request with {len(messages)} messages")
        
        # Prepare API request
        request_data = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        print(f"DEBUG: Request data prepared, encoding JSON")
        
        # Create HTTP request
        req = urllib.request.Request(
            api_endpoint,
            data=json.dumps(request_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        
        print(f"DEBUG: HTTP request created, sending to API...")
        
        # Send request and get response
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"DEBUG: Got response from API, parsing JSON")
            raw_response = response.read().decode('utf-8')
            print(f"DEBUG: Raw response length: {len(raw_response)}")
            print(f"DEBUG: Raw response (first 500 chars): {raw_response[:500]}")
            
            response_data = json.loads(raw_response)
            print(f"DEBUG: JSON parsed successfully")
            print(f"DEBUG: Response keys: {response_data.keys()}")
            
            # Extract response text
            if 'choices' in response_data and len(response_data['choices']) > 0:
                message = response_data['choices'][0]['message']
                
                # Check for content (standard response)
                if message.get('content'):
                    result = message['content']
                    print(f"DEBUG: Extracted content, length: {len(result)}")
                    
                    # Clean up the response - extract only HTML table if present
                    import re
                    
                    # Look for table wrapped in div
                    div_match = re.search(r'(<div\s+class=["\']table-responsive["\']>.*?</div>)', result, re.DOTALL | re.IGNORECASE)
                    if div_match:
                        print(f"DEBUG: Found table with wrapper div")
                        return div_match.group(1)
                    
                    # Look for standalone table
                    table_match = re.search(r'(<table[^>]*>.*?</table>)', result, re.DOTALL | re.IGNORECASE)
                    if table_match:
                        print(f"DEBUG: Found standalone HTML table")
                        table_html = f'<div class="table-responsive">{table_match.group(1)}</div>'
                        return table_html
                    
                    # If no HTML found, return as-is (for text responses)
                    return result
                # Check for reasoning field (reasoning models)
                elif message.get('reasoning'):
                    reasoning = message['reasoning']
                    print(f"DEBUG: Got reasoning response, length: {len(reasoning)}")
                    
                    # Just return the reasoning text as-is - let the AI decide format
                    return reasoning
                else:
                    print(f"DEBUG: No content or reasoning field found. Message: {message}")
                    return "I received a response but couldn't extract the content. Please try again."
            else:
                print(f"DEBUG: Unexpected response format: {response_data}")
                return "I received an unexpected response format. Please try again."
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else 'No error details'
        app.logger.error(f"API HTTP Error {e.code}: {error_body}")
        print(f"DEBUG: HTTP Error {e.code} calling {api_endpoint}: {error_body}")
        return f"Sorry, the AI service is temporarily unavailable (HTTP {e.code}). Please try again later."
    
    except urllib.error.URLError as e:
        app.logger.error(f"API Connection Error: {str(e)}")
        print(f"DEBUG: URL Error calling {api_endpoint}: {str(e)}")
        return f"Sorry, cannot connect to AI service: {str(e)}"
    
    except Exception as e:
        app.logger.error(f"Error generating response: {str(e)}")
        print(f"DEBUG: Exception in generate_response: {type(e).__name__}: {str(e)}")
        print(f"DEBUG: API endpoint: {api_endpoint}, API key: {'***' + api_key[-4:] if api_key and len(api_key) > 4 else 'MISSING'}")
        # Fallback to simple pattern matching
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ['help', 'what can', 'can you']):
            return """I'm your Business Intelligence Assistant. I can help with:

📊 Analytics & Reporting - View recent orders and statistics
🔍 Search & Lookup - Find specific orders and supplier information
💡 Insights & Analysis - Ask about trends in your data

Just ask about your shipping data, suppliers, carriers, or orders!"""
        
        return f"I'm having trouble connecting to my AI service. Here's what I can tell you from the database:\n\n{context}"

# ============================================================================
# SHIPPING MANAGEMENT ROUTES
# ============================================================================

@app.route('/createshipping', methods=['GET', 'POST'])
def createshipping():
    if request.method == 'POST':
        supplier_name = request.form.get('supplier_name', '').strip()
        order_date = request.form.get('order_date', '').strip()
        exp_delivery_date = request.form.get('exp_delivery_date', '').strip()
        actual_delivery_date = request.form.get('actual_delivery_date', '').strip()
        tracking_number = request.form.get('tracking_number', '').strip()
        shipping_carrier = request.form.get('shipping_carrier', '').strip()
        item_name = request.form.get('item_name', '').strip()
        quantity = request.form.get('quantity', '').strip()
        order_total = request.form.get('order_total', '').strip()
        notes = request.form.get('notes', '').strip()
        
        errors = []
        if not supplier_name:
            errors.append('Supplier Name is required')
        if not order_date:
            errors.append('Order Date is required')
        if not tracking_number:
            errors.append('Tracking Number is required')
        if not item_name:
            errors.append('Item Name is required')
        if not quantity:
            errors.append('Order Quantity is required')
        if not order_total:
            errors.append('Order Total is required')
        
        if errors:
            return {'success': False, 'errors': errors}, 400
        
        try:
            sql = """INSERT INTO Shipping 
                     (supplier_name, order_date, exp_delivery_date, actual_delivery_date, tracking_number, 
                      shipping_carrier, item_name, quantity, order_total, notes) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            
            params = (supplier_name, order_date, exp_delivery_date if exp_delivery_date else None,
                     actual_delivery_date if actual_delivery_date else None, tracking_number,
                     shipping_carrier if shipping_carrier else None, item_name, int(quantity),
                     float(order_total), notes if notes else 'N/A')
            
            cursor.execute(sql, params)
            db_connection.commit()
            shipping_id = cursor.lastrowid
            
            return {'success': True, 'shipping_id': shipping_id, 'message': 'Shipping record created successfully'}
        except Exception as e:
            db_connection.rollback()
            return {'success': False, 'errors': [str(e)]}, 500
    
    return render_template('shipping_create.html')

@app.route('/modifyshipping')
def modifyshipping():
    return render_template('shipping_modify.html')

@app.route('/deleteshipping')
def deleteshipping():
    return render_template('shipping_delete.html')

@app.route('/search')
def search_page():
    return render_template('shipping_search.html')

@app.route('/searchorder', methods=['GET'])
def searchorder():
    shipping_id = request.args.get('shipping_id', '').strip()
    if not shipping_id:
        return {'success': False, 'error': 'Shipping ID is required'}, 400
    
    try:
        cursor.execute("SELECT * FROM Shipping WHERE shipping_id = %s", (shipping_id,))
        order = cursor.fetchone()
        if order:
            return render_template('shipping_searchtable.html', orders=[order])
        else:
            return {'success': False, 'error': 'Order not found'}, 404
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/updateshipping', methods=['POST'])
def updateshipping():
    shipping_id = request.form.get('shipping_id')
    supplier_name = request.form.get('supplier_name', '').strip()
    order_date = request.form.get('order_date', '').strip()
    exp_delivery_date = request.form.get('exp_delivery_date', '').strip()
    actual_delivery_date = request.form.get('actual_delivery_date', '').strip()
    tracking_number = request.form.get('tracking_number', '').strip()
    shipping_carrier = request.form.get('shipping_carrier', '').strip()
    item_name = request.form.get('item_name', '').strip()
    quantity = request.form.get('quantity', '').strip()
    order_total = request.form.get('order_total', '').strip()
    notes = request.form.get('notes', '').strip()
    
    try:
        sql = """UPDATE Shipping SET supplier_name=%s, order_date=%s, exp_delivery_date=%s, 
                 actual_delivery_date=%s, tracking_number=%s, shipping_carrier=%s, item_name=%s, 
                 quantity=%s, order_total=%s, notes=%s WHERE shipping_id=%s"""
        
        params = (supplier_name, order_date, exp_delivery_date if exp_delivery_date else None,
                 actual_delivery_date if actual_delivery_date else None, tracking_number,
                 shipping_carrier if shipping_carrier else None, item_name, int(quantity),
                 float(order_total), notes if notes else 'N/A', shipping_id)
        
        cursor.execute(sql, params)
        db_connection.commit()
        
        return {'success': True, 'message': 'Shipping record updated successfully'}
    except Exception as e:
        db_connection.rollback()
        return {'success': False, 'error': str(e)}, 500

@app.route('/deleterecord', methods=['POST'])
def deleterecord():
    shipping_id = request.json.get('shipping_id')
    if not shipping_id:
        return {'success': False, 'error': 'Shipping ID is required'}, 400
    
    try:
        cursor.execute("DELETE FROM Shipping WHERE shipping_id = %s", (shipping_id,))
        db_connection.commit()
        return {'success': True, 'message': 'Record deleted successfully'}
    except Exception as e:
        db_connection.rollback()
        return {'success': False, 'error': str(e)}, 500

@app.route('/getallrecords', methods=['GET'])
def getallrecords():
    sort_by = request.args.get('sort_by', '')
    carrier = request.args.get('carrier', '')
    
    sql = "SELECT * FROM Shipping WHERE 1=1"
    params = []
    
    if carrier:
        sql += " AND shipping_carrier = %s"
        params.append(carrier)
    
    if sort_by == 'supplier_asc':
        sql += " ORDER BY supplier_name ASC"
    elif sort_by == 'supplier_desc':
        sql += " ORDER BY supplier_name DESC"
    elif sort_by == 'date_asc':
        sql += " ORDER BY order_date ASC"
    elif sort_by == 'date_desc':
        sql += " ORDER BY order_date DESC"
    
    try:
        cursor.execute(sql, tuple(params))
        orders = cursor.fetchall()
        return render_template('shipping_searchtable.html', orders=orders)
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/searchorders', methods=['GET'])
def searchorders():
    shipping_id = request.args.get('shipping_id', '').strip()
    supplier_name = request.args.get('supplier_name', '').strip()
    carrier = request.args.get('shipping_carrier', '')
    sort_date = request.args.get('sort_date', '')
    sort_item = request.args.get('sort_item', '')
    sort_total = request.args.get('sort_total', '')
    
    sql = "SELECT * FROM Shipping WHERE 1=1"
    params = []
    
    if shipping_id:
        sql += " AND shipping_id LIKE %s"
        params.append(f"%{shipping_id}%")
    
    if supplier_name:
        sql += " AND supplier_name LIKE %s"
        params.append(f"%{supplier_name}%")
    
    if carrier:
        sql += " AND shipping_carrier = %s"
        params.append(carrier)
    
    order_clauses = []
    if sort_date == 'date_asc':
        order_clauses.append("order_date ASC")
    elif sort_date == 'date_desc':
        order_clauses.append("order_date DESC")
    
    if sort_item == 'item_asc':
        order_clauses.append("item_name ASC")
    elif sort_item == 'item_desc':
        order_clauses.append("item_name DESC")
    
    if sort_total == 'total_asc':
        order_clauses.append("order_total ASC")
    elif sort_total == 'total_desc':
        order_clauses.append("order_total DESC")
    
    if order_clauses:
        sql += " ORDER BY " + ", ".join(order_clauses)
    
    try:
        cursor.execute(sql, tuple(params))
        orders = cursor.fetchall()
        return render_template('shipping_searchtable.html', orders=orders)
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

# ============================================================================
# VISUALIZATION ROUTE
# ============================================================================

@app.route('/visual')
def visual():
    """Render the visualization dashboard with charts and statistics"""
    try:
        # Get total orders
        cursor.execute("SELECT COUNT(*) as total FROM Shipping")
        total_orders = cursor.fetchone()['total']
        
        # Get orders delivered (has actual_delivery_date)
        cursor.execute("SELECT COUNT(*) as delivered FROM Shipping WHERE actual_delivery_date IS NOT NULL")
        orders_delivered = cursor.fetchone()['delivered']
        
        # Get orders in transit (no actual_delivery_date)
        cursor.execute("SELECT COUNT(*) as in_transit FROM Shipping WHERE actual_delivery_date IS NULL")
        orders_in_transit = cursor.fetchone()['in_transit']
        
        # Get total costs by supplier for pie chart
        cursor.execute("""
            SELECT supplier_name, SUM(order_total) as total_cost 
            FROM Shipping 
            GROUP BY supplier_name 
            ORDER BY total_cost DESC
        """)
        supplier_data = cursor.fetchall()
        
        # Get top supplier by total spending
        top_supplier = supplier_data[0] if supplier_data else {'supplier_name': 'N/A', 'total_cost': 0}
        
        # Get monthly cost analysis - group all orders by month
        cursor.execute("""
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m') as month,
                DATE_FORMAT(order_date, '%M %Y') as month_label,
                SUM(order_total) as monthly_cost,
                COUNT(*) as order_count
            FROM Shipping
            GROUP BY DATE_FORMAT(order_date, '%Y-%m'), DATE_FORMAT(order_date, '%M %Y')
            ORDER BY month DESC
            LIMIT 12
        """)
        monthly_costs_raw = cursor.fetchall()
        # Reverse to show oldest to newest
        monthly_costs = list(reversed(monthly_costs_raw))
        
        # Get orders by carrier for bar chart
        cursor.execute("""
            SELECT 
                COALESCE(shipping_carrier, 'Unknown') as carrier,
                COUNT(*) as order_count
            FROM Shipping
            GROUP BY shipping_carrier
            ORDER BY order_count DESC
        """)
        carrier_data = cursor.fetchall()
        
        # Prepare statistics dictionary
        stats = {
            'total_orders': total_orders,
            'orders_delivered': orders_delivered,
            'orders_in_transit': orders_in_transit,
            'top_supplier_name': top_supplier['supplier_name'],
            'top_supplier_cost': top_supplier['total_cost']
        }
        
        return render_template('shipping_visual.html', 
                             stats=stats, 
                             supplier_data=supplier_data,
                             monthly_costs=monthly_costs,
                             carrier_data=carrier_data)
    
    except Exception as e:
        app.logger.error(f"Error in visual route: {str(e)}")
        return {'success': False, 'error': str(e)}, 500