import os
import pandas as pd
from flask import Flask, request, render_template, jsonify, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'supersecretkey'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.xlsx'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        session['filepath'] = filepath
        try:
            df = pd.read_excel(filepath)
            # if 'Drug' not in df.columns or 'Alternate' not in df.columns:
            #     return jsonify({'error': 'Excel file must contain "Drug" and "Alternate" columns'}), 400
            # Automatically use first two columns as Drug & Alternate
            df = df.iloc[:,:2]
            df.columns = ['Drug', 'Alternate']
            return jsonify({'success': 'File uploaded and processed successfully', 'rows': len(df), 'columns': list(df.columns)}), 200
        except Exception as e:
            return jsonify({'error': f'Error processing file: {e}'}), 500
    else:
        return jsonify({'error': 'Invalid file type, please upload a .xlsx file'}), 400

@app.route('/search', methods=['GET'])
def search_drug():
    query = request.args.get('query', '')
    filepath = session.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'No file uploaded or file not found. Please upload a file first.'}), 400
    if not query:
        return jsonify({'results': []})

    try:
        df = pd.read_excel(filepath)
        # Automatically use first two columns as Drug & Alternate
        df = df.iloc[:,:2]
        df.columns = ['Drug', 'Alternate']
        results = []
        # Search in 'Drug' column
        drug_matches = df[df['Drug'].str.contains(query, case=False, na=False)]
        for _, row in drug_matches.iterrows():
            results.append({
                'type': 'Found as Drug',
                'drug': row['Drug'],
                'alternate': row['Alternate']
            })

        # Search in 'Alternate' column
        alt_matches = df[df['Alternate'].str.contains(query, case=False, na=False)]
        for _, row in alt_matches.iterrows():
            # Avoid duplicates if a drug is also an alternative
            if not any(d['drug'] == row['Drug'] and d['alternate'] == row['Alternate'] for d in results):
                results.append({
                    'type': 'Found as Alternative',
                    'drug': row['Drug'],
                    'alternate': row['Alternate']
                })
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': f'Error searching file: {e}'}), 500

if __name__ == '__main__':
    app.run(debug=True)