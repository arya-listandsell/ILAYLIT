import pandas as pd

# List of known multi-word color names
MULTI_WORD_COLORS = {'Off White','Flash Green','Ice Blue','Dark Blue','Baby Rosa'}

output_file = 'test_outputsheet.csv'
df_input = pd.read_csv('test_inputsheet.csv')
df_output = pd.read_csv('test_outputsheet.csv')
df_images = pd.read_csv('images.csv')

# Get unique mainnumbers from input that aren't in output
missing_mainnumbers = set(df_input['mainnumber']) - set(df_output['Variant SKU'])
if missing_mainnumbers:
    # First, collect all products and analyze their variations
    product_groups = {}
    for _, row in df_input.iterrows():
        if row['mainnumber'] in missing_mainnumbers:
            product_name = row['name']
            name_parts = product_name.split()
            
            # Initialize variables
            color = ''
            base_name = product_name
            
            if len(name_parts) >= 2:
                last_two_words = ' '.join(name_parts[-2:])
                if last_two_words.lower() in {c.lower() for c in MULTI_WORD_COLORS}:
                    color = last_two_words
                    base_name = ' '.join(name_parts[:-2])

            
            # If no two-word color found, proceed with original logic
            if not color and len(name_parts) > 1:
                # Original logic - check if last word is color when base names match
                base_name_candidate = ' '.join(name_parts[:-1])
                color_candidate = name_parts[-1]
                
                # We'll confirm this is actually a color variant later when we group products
                color = color_candidate
                base_name = base_name_candidate
            
            if base_name not in product_groups:
                product_groups[base_name] = {
                    'has_color_variants': False,
                    'full_names': set(),  # Track all full names for this base
                    'mainnumbers': set(),
                    'sizes': set(),
                    'variants': [],
                    'product_data': {}
                }
            product_groups[base_name]['full_names'].add(product_name)
            # Check for configurator options (sizes)
            size = ''
            if 'configuratorOptions' in row and pd.notna(row['configuratorOptions']):
                options = row['configuratorOptions'].split(':')
                if len(options) >= 2:
                    size = options[1].strip()
                    product_groups[base_name]['sizes'].add(size)
            # Store the variant data
            product_groups[base_name]['variants'].append({
                'mainnumber': row['mainnumber'],
                'size': size,
                'color': color,
                'full_name': product_name,  # Store the full original name
                'data': row
            })
            product_groups[base_name]['mainnumbers'].add(row['mainnumber'])
    
    # Determine which products have color variants by analyzing name patterns
    for base_name, group in product_groups.items():
        # Collect all unique endings (potential colors)
        endings = set()
        for full_name in group['full_names']:
            name_parts = full_name.split()
            base_parts = base_name.split()
            if len(name_parts) > len(base_parts):
                # Get the trailing words as potential color
                ending = ' '.join(name_parts[len(base_parts):])
                endings.add(ending)
        
        # If there are multiple endings, treat as color variants
        if len(endings) > 1:
            group['has_color_variants'] = True
            group['display_name'] = base_name
            # Update color for each variant
            for variant in group['variants']:
                full_name = variant['full_name']
                name_parts = full_name.split()
                base_parts = base_name.split()
                if len(name_parts) > len(base_parts):
                    variant['color'] = ' '.join(name_parts[len(base_parts):])
        else:
            group['has_color_variants'] = False
            group['display_name'] = base_name

    
    # Rest of the code remains the same...
    new_rows = []
    handles_with_html = set()  # Track which handles already have HTML content
    # Process each product group
    for base_name, group in product_groups.items():
        display_name = group['display_name']
        # Get common product info from first variant
        first_variant = group['variants'][0]['data']
        html_body = first_variant.get('description_long', '')
        vendor = first_variant.get('supplier', '')
        keywords = first_variant.get('tags', '')
        # Process each mainnumber in this product group
        for mainnumber in sorted(group['mainnumbers']):
            # Get images specific to this mainnumber
            image_urls = []
            if mainnumber in df_images['mainnumber'].values:
                image_row = df_images[df_images['mainnumber'] == mainnumber].iloc[0]
                if pd.notna(image_row['imageUrl']):
                    image_urls = [url.strip() for url in image_row['imageUrl'].split('|') if url.strip()]
            # Create variants for this mainnumber
            variant_counter = 1
            image_position = 1
            # Determine the handle for this product
            if group['has_color_variants']:
                handle = display_name.replace(' ', '-').lower()
            else:
                handle = next(iter(group['full_names'])).replace(' ', '-').lower()
            # Check if we've already added HTML for this handle
            html_body_added = handle in handles_with_html
            for variant in [v for v in group['variants'] if v['mainnumber'] == mainnumber]:
                variant_data = variant['data']
                size = variant['size']
                color = variant['color']
                full_name = variant['full_name']
                variant_price = variant_data.get('price_EK', '')
                Variant_compare_price = variant_data.get('pseudoprice_EK', '')
                inventory_qty = variant_data.get('instock', 1)
                # Create variant SKU - mainnumber for first variant, then with counter
                variant_sku = mainnumber if variant_counter == 1 else f"{mainnumber}.{variant_counter-1}"
                # For ALL variants, use display_name in Title (base name without color)
                current_title = display_name
                image_url = image_urls[0] if image_urls else ''
                # Prepare the row data
                row_data = {
                    'Vendor': vendor,
                    'Title': current_title,
                    'Handle': handle,
                    'Body (HTML)': html_body if not html_body_added and variant_counter == 1 else '',
                    'Variant SKU': variant_sku,
                    'Variant Price': variant_price,
                    'Variant Compare At Price': Variant_compare_price,
                    'Variant Inventory Qty': 1 if inventory_qty==0 else inventory_qty,
                    'Product Category': keywords,
                    'Tags': keywords,
                    'Image Src': image_url,
                    'Variant Image': image_url,
                    'Published': 'TRUE' if variant_counter == 1 else '',
                    'Variant Grams': int(0),
                    'Variant Inventory Tracker': 'shopify',
                    'Variant Inventory Policy': 'deny',
                    'Variant Fulfillment Service': 'manual',
                    'Variant Requires Shipping': 'TRUE',
                    'Variant Taxable': 'TRUE',
                    'Image Position': image_position if image_url else '',
                    'Gift Card': 'FALSE',
                    'Variant Weight Unit': 'kg',
                    'Status': 'active' if variant_counter == 1 else ''
                }
                # Mark that we've added HTML for this handle if this is the first variant
                if not html_body_added and variant_counter == 1 and html_body:
                    handles_with_html.add(handle)
                    html_body_added = True
                if image_url:
                    image_urls.pop(0)
                # Add size option if exists
                if size:
                    row_data.update({
                        'Option1 Name': 'Größe',
                        'Option1 Value': size
                    })
                # Add color option only if product has color variants
                if group['has_color_variants'] and color:
                    row_data.update({
                        'Option2 Name': 'Farbe',
                        'Option2 Value': color
                    })
                new_rows.append(row_data)
                if image_urls:
                    image_position += 1
                variant_counter += 1
            # Add remaining image URLs with empty Variant SKU
            for url in image_urls:
                new_rows.append({
                    'Title': '',
                    'Handle': handle,
                    'Body (HTML)': '',
                    'Variant SKU': '',
                    'Image Src': url,
                    'Image Position': image_position,
                })
                image_position += 1
    # Create DataFrame from new rows
    df_to_add = pd.DataFrame(new_rows)
    # Ensure all required columns exist in output
    all_columns = [
        'Vendor', 'Title', 'Handle', 'Body (HTML)', 
        'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value',
        'Variant SKU', 'Variant Price', 'Variant Compare At Price', 'Variant Inventory Qty',
        'Product Category', 'Tags', 'Image Src', 'Variant Image','Published', 'Variant Grams',
        'Variant Inventory Tracker', 'Variant Inventory Policy',
        'Variant Fulfillment Service', 'Variant Requires Shipping',
        'Variant Taxable', 'Image Position', 'Gift Card',
        'Variant Weight Unit', 'Status'
    ]
    for col in all_columns:
        if col not in df_output.columns:
            df_output[col] = ''
    # Append to output and save
    df_output = pd.concat([df_output, df_to_add], ignore_index=True)
    df_output.to_csv(output_file, index=False)
    print(f"Added {len(new_rows)} rows ")
    print('File Name : ',output_file)
else:
    print("All mainnumbers already exist in output file")
    print('File Name : ',output_file)
