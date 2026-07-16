from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_date
from datetime import datetime
from Report.models import ReportFile,ReportFileDetail
from Report import Configs
from openpyxl.utils import get_column_letter


import pymysql
import pandas as pd
from datetime import datetime


# For visualizations
import matplotlib.pyplot as plt
from io import BytesIO

# For formatting
import re
from django.http import JsonResponse, HttpResponse
import os
import pandas as pd
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
import zeep
import uuid
import xml.etree.ElementTree as ET
from .models import FileProcessSetting
from typing import List
from tempfile import NamedTemporaryFile
from io import StringIO

UPLOAD_TYPE_LABELS = {
    'transactionsfile': 'Transaction File',
    'batchfile': 'Batch Transfer File',
    'customerfile': 'Customer Data File',
    'accountsfile': 'Customer Accounts File',
    'ovewrdraftfile': 'Overdraft Data File',
    'salaryfile': 'Salary File',
}

@csrf_exempt
def DataUpload_view(request, *args, **kwargs):
    if request.method == 'POST':
        # Check if the transaction file is present (required field)

        first_record = FileProcessSetting.objects.first()

        if first_record:
            endpoint_address = first_record.EndpointAddress
            invalid_account_ledger = first_record.InvalidAccountLedger
            endpoint_address2 = first_record.EndpointAddress2

        # Get the uploaded files
        transaction_file = request.FILES.get('transactionsfile')
        batch_transfer_files = request.FILES.getlist('batchfile')
        customer_data_file = request.FILES.get('customerfile')
        customer_accounts_file = request.FILES.get('accountsfile')
        overdraft_data_file = request.FILES.get('ovewrdraftfile')
        salary_file = request.FILES.get('salaryfile')
        uploaded_frames = {}
        upload_counts = {}

        uploads_present = any([
            transaction_file,
            batch_transfer_files,
            customer_data_file,
            customer_accounts_file,
            overdraft_data_file,
            salary_file
        ])

        print(uploads_present,'-uploaded')
        if not uploads_present:
            messages.error(request, 'No Transaction/Data file was not uploaded!!')
            return render(request, 'fileupload.html')

        def add_uploaded_dataset(dataset_key, dataframe, valid_total=None, invalid_total=None):
            if dataframe is None:
                return
            if valid_total is None or invalid_total is None:
                if 'Status' in dataframe.columns:
                    valid_total = sum(1 for data in dataframe.itertuples() if getattr(data, 'Status', '') == 'Valid')
                    invalid_total = sum(1 for data in dataframe.itertuples() if getattr(data, 'Status', '') == 'Invalid')
                else:
                    valid_total = len(dataframe.index)
                    invalid_total = 0
            uploaded_frames.setdefault(dataset_key, [])
            upload_counts.setdefault(dataset_key, {'valid': 0, 'invalid': 0})
            uploaded_frames[dataset_key].append(dataframe)
            upload_counts[dataset_key]['valid'] += valid_total
            upload_counts[dataset_key]['invalid'] += invalid_total

        upload_summaries = {}
        try:

            if transaction_file:
                dataset = process_uploaded_file(transaction_file)
                dataset['Status'] = ''

                print('starting validation')

                #Loop and validate that all accounts are valid:
                wsdl = endpoint_address
                client = zeep.Client(wsdl=wsdl)

                first_record = FileProcessSetting.objects.first()

                if first_record:
                    host = first_record.Corehost
                    port = first_record.Coreport
                    database = first_record.Coredatabase
                    username = first_record.Coreusername
                    password = first_record.Corepassword

                connection = connect_to_mysql(host, port, database, username, password)
                
                # Create a cursor and establish the connection before the loop
                cursor = connection.cursor()

                for index, row in dataset.iterrows():
                    idAccount = str(row['AccountID'])  # Assuming 'AccountID' is the column name
                    OldAccountID = str(row['OldAccountID'])  # Assuming 'OldAccountID' is the column name
                    IDNumber = str(row['IDNumber'])  # Assuming 'IDNumber' is the column name
                    MobileNumber = str(row['MobileNumber'])  # Assuming 'MobileNumber' is the column name
                    AccountType = str(row['Account Type'])  # Assuming 'MobileNumber' is the column name
                    
                    print('Validating AccountID:', idAccount, ' OldAccountID:', OldAccountID, ' IDNumber:', IDNumber, ' MobileNumber:', MobileNumber)

                    try:
                        if AccountType == 'G':
                            query = "SELECT GLAccountID FROM tb_generalledger WHERE GLACCOUNTID = %s"
                            cursor.execute(query, (idAccount,))
                            result = cursor.fetchone()

                            if result:
                                account_id = result['GLAccountID']
                                dataset.at[index, 'Status'] = 'Valid'
                                dataset.at[index, 'AccountID'] = account_id
                            else:
                                dataset.at[index, 'Status'] = 'Invalid'
                                dataset.at[index, 'AccountID'] = invalid_account_ledger
                                dataset.at[index, 'Account Type'] = 'G'
                                dataset.at[index, 'Remarks'] = 'Invalid General Ledger Account - Posted to Suspense: ' + str(idAccount)

                        else:
                            query = "SELECT AccountID FROM tb_accountcustomer WHERE ACCOUNTSTATUSID <> 'AC' and ACCOUNTID = %s"
                            cursor.execute(query, (idAccount,))
                            result = cursor.fetchone()

                            if result:
                                account_id = result['AccountID']
                                dataset.at[index, 'Status'] = 'Valid'
                                dataset.at[index, 'AccountID'] = account_id

                            else:
                                query = "SELECT AccountID FROM tb_accountcustomer WHERE ACCOUNTSTATUSID <> 'AC' and OLDACCOUNTID = %s"
                                cursor.execute(query, (OldAccountID,))
                                result = cursor.fetchone()
                                
                                if result:
                                    account_id = result['AccountID']
                                    dataset.at[index, 'Status'] = 'Valid'
                                    dataset.at[index, 'AccountID'] = account_id

                                else:
                                    query = "SELECT AccountID FROM tb_accountcustomer WHERE ACCOUNTSTATUSID <> 'AC' and MOBILE = %s"
                                    cursor.execute(query, (MobileNumber,))
                                    result = cursor.fetchone()

                                    if result:
                                        account_id = result['AccountID']
                                        dataset.at[index, 'Status'] = 'Valid'
                                        dataset.at[index, 'AccountID'] = account_id

                                    else:
                                        query = """
                                        SELECT ac.AccountID, cm.CustomerId
                                        FROM tb_accountcustomer ac
                                        JOIN tb_customermaster cm ON ac.CLIENTID = cm.CUSTOMERID
                                        AND cm.IDNO = %s
                                         and ACCOUNTSTATUSID <> 'AC' 
                                         order by ac.AccountID desc
                                        """
                                        cursor.execute(query, (IDNumber))
                                        result = cursor.fetchone()
                                        
                                        if result:
                                            account_id = result['AccountID']
                                            dataset.at[index, 'Status'] = 'Valid'
                                            dataset.at[index, 'AccountID'] = account_id
                                        else:
                                            dataset.at[index, 'Status'] = 'Invalid'
                                            dataset.at[index, 'AccountID'] = invalid_account_ledger
                                            dataset.at[index, 'Account Type'] = 'G'
                                            dataset.at[index, 'Remarks'] = f'Invalid Account {IDNumber},{MobileNumber},{OldAccountID},{idAccount},- Posted to Suspense: ' + str(idAccount)

                    except zeep.exceptions.Fault as fault:
                        print(f"SOAP Fault for AccountID {idAccount}: {fault}")
                        dataset.at[index, 'Status'] = 'Invalid'
                        
                    except Exception as e:
                        print(str(e))
                        print('--------------------')
                        print(f"Error for AccountID {idAccount}: {str(e)}")

                # Close the cursor and connection after the loop
                cursor.close()
                connection.close()

                valid_count = sum(1 for data in dataset.itertuples() if data.Status == 'Valid')
                invalid_count = sum(1 for data in dataset.itertuples() if data.Status == 'Invalid')

                print(valid_count,invalid_count)
                add_uploaded_dataset('transactionsfile', dataset, valid_count, invalid_count)

            # Process additional files if provided
            if batch_transfer_files:
                batch_datasets = []
                for file in batch_transfer_files:
                    batch_datasets.append(process_uploaded_file(file))
                if batch_datasets:
                    batch_dataset = pd.concat(batch_datasets, ignore_index=True)
                    add_uploaded_dataset('batchfile', batch_dataset, len(batch_dataset.index), 0)
            
            if customer_data_file:
                customer_dataset = process_uploaded_file(customer_data_file)
                add_uploaded_dataset('customerfile', customer_dataset, len(customer_dataset.index), 0)
            
            if customer_accounts_file:
                accounts_dataset = process_uploaded_file(customer_accounts_file)
                add_uploaded_dataset('accountsfile', accounts_dataset, len(accounts_dataset.index), 0)

            if overdraft_data_file:
                overdraft_dataset = process_uploaded_file(overdraft_data_file)
                add_uploaded_dataset('ovewrdraftfile', overdraft_dataset, len(overdraft_dataset.index), 0)

            if salary_file:
                salary_dataset = process_uploaded_file(salary_file)
                add_uploaded_dataset('salaryfile', salary_dataset, len(salary_dataset.index), 0)
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')

        if not uploaded_frames:
            return render(request, 'fileupload.html')

        for dataset_key, frames in uploaded_frames.items():
            combined_df = pd.concat(frames, ignore_index=True)
            safe_df = combined_df.fillna('')
            upload_summaries[dataset_key] = {
                'label': UPLOAD_TYPE_LABELS.get(dataset_key, 'Uploaded Data'),
                'headers': safe_df.columns.tolist(),
                'rows': safe_df.values.tolist(),
                'records': safe_df.to_dict('records'),
                'valid_count': upload_counts[dataset_key]['valid'],
                'invalid_count': upload_counts[dataset_key]['invalid'],
            }

        upload_tabs = []
        for key, label in UPLOAD_TYPE_LABELS.items():
            upload_tabs.append({
                'key': key,
                'label': label,
                'summary': upload_summaries.get(key)
            })

        processed_labels = [tab['label'] for tab in upload_tabs if tab['summary']]
        if processed_labels:
            messages.success(request, f"Successfully processed: {', '.join(processed_labels)}")

        transaction_summary = upload_summaries.get('transactionsfile')
        file_details = transaction_summary['records'] if transaction_summary else []
        headers = transaction_summary['headers'] if transaction_summary else []

        request.session['file_details'] = file_details
        request.session['headers'] = headers
        request.session['upload_type'] = 'transactionsfile' if transaction_summary else None

        session_datasets = {key: summary['records'] for key, summary in upload_summaries.items() if summary}
        session_headers = {key: summary['headers'] for key, summary in upload_summaries.items() if summary}
        request.session['uploaded_datasets'] = session_datasets
        request.session['uploaded_headers'] = session_headers

        summary_counts = [
            {
                'label': tab['label'],
                'valid': tab['summary']['valid_count'],
                'invalid': tab['summary']['invalid_count'],
            }
            for tab in upload_tabs if tab['summary']
        ]

        total_valid = sum(summary['valid'] for summary in summary_counts)
        total_invalid = sum(summary['invalid'] for summary in summary_counts)
        upload_type_label = transaction_summary['label'] if transaction_summary else (processed_labels[0] if processed_labels else 'Uploaded Data')

        return render(request, 'fileuploaddetails.html', {
            'FileDetails': file_details,
            'headers': headers,
            'valid_count': total_valid,
            'invalid_count': total_invalid,
            'upload_tabs': upload_tabs,
            'upload_type_label': upload_type_label,
            'summary_counts': summary_counts,
        })
    else:
        return render(request,"fileupload.html",{})

def ReconUpload_view(request):
    """
    Upload reconciliation file, expose column headers, and allow mapping to static fields.
    """
    static_fields: List[str] = ['Date', 'Amount', 'AccountNo', 'Description', 'RefNo']
    context = {
        'static_fields': static_fields,
    }

    # Reuse any data already in session so the user can retry mapping without re-uploading.
    session_records = request.session.get('recon_dataset', [])
    session_headers = request.session.get('recon_headers', [])
    if session_records and session_headers:
        preview_table = [
            [row.get(col, '') for col in session_headers]
            for row in session_records[:10]
        ]
        context.update({
            'headers': session_headers,
            'preview_rows': preview_table,
            'has_data': True,
            'record_count': len(session_records),
        })

    if request.method == 'POST':
        recon_file = request.FILES.get('reconfile')
        if not recon_file:
            messages.error(request, 'Please select a reconciliation file to upload.')
            return render(request, 'reconupload.html', context)

        try:
            dataset = process_uploaded_file(recon_file).fillna('')
        except Exception as e:
            messages.error(request, f'Error reading file: {str(e)}')
            return render(request, 'reconupload.html', context)

        records = dataset.to_dict(orient='records')
        headers = dataset.columns.tolist()

        request.session['recon_dataset'] = records
        request.session['recon_headers'] = headers

        preview_table = [
            [row.get(col, '') for col in headers]
            for row in records[:10]
        ]

        context.update({
            'headers': headers,
            'preview_rows': preview_table,
            'has_data': True,
            'uploaded_filename': recon_file.name,
            'record_count': len(records),
        })

        messages.success(request, f'Loaded {len(records)} records from {recon_file.name}. Map the columns to continue.')

    return render(request, 'reconupload.html', context)

def build_recon_json(request):
    """
    Build JSON payload for reconciliation data using user-provided column mappings.
    """
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    recon_records = request.session.get('recon_dataset', [])
    if not recon_records:
        return JsonResponse({'message': 'No reconciliation data found. Upload a file first.'}, status=400)

    mapping, error = _parse_recon_mapping(request)
    if error:
        return error

    mapped_records = _apply_recon_mapping(recon_records, mapping)

    preview = mapped_records[:20]
    response = {
        'mapping': mapping,
        'preview': preview,
        'total': len(mapped_records),
        'records': mapped_records,
    }

    return JsonResponse(response)

def run_recon(request):
    """
    Execute reconciliation by matching mapped records against tb_transactions.
    Stores reconciled/unreconciled lists in session for CSV download.
    """
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    recon_records = request.session.get('recon_dataset', [])
    if not recon_records:
        return JsonResponse({'message': 'No reconciliation data found. Upload a file first.'}, status=400)

    mapping, error = _parse_recon_mapping(request)
    if error:
        return error

    mapped_records = _apply_recon_mapping(recon_records, mapping)

    first_record = FileProcessSetting.objects.first()
    if first_record:
        host = first_record.Corehost
        port = first_record.Coreport
        database = first_record.Coredatabase
        username = first_record.Coreusername
        password = first_record.Corepassword
    else:
        return JsonResponse({'message': 'Database settings not configured.'}, status=500)

    connection = connect_to_mysql(host, port, database, username, password)
    if connection is None:
        return JsonResponse({'message': 'Unable to connect to the transactions database.'}, status=500)

    reconciled = []
    unreconciled = []
    try:
        cursor = connection.cursor()
        for row in mapped_records:
            account_id = str(row.get('AccountNo', '')).strip()
            trx_date = normalize_date(row.get('Date'))
            amount = normalize_amount(row.get('Amount'))

            if not account_id or trx_date is None or amount is None:
                row_copy = dict(row)
                row_copy['ReconcileStatus'] = 'Invalid data'
                unreconciled.append(row_copy)
                continue

            query = """
                SELECT 1
                FROM tb_transactions
                WHERE ACCOUNTID = %s
                  AND TRXDATE = %s
                  AND TRXAMOUNT = %s
                LIMIT 1
            """
            cursor.execute(query, (account_id, trx_date, amount))
            match = cursor.fetchone()

            row_copy = dict(row)
            if match:
                row_copy['ReconcileStatus'] = 'Reconciled'
                reconciled.append(row_copy)
            else:
                row_copy['ReconcileStatus'] = 'Unreconciled'
                unreconciled.append(row_copy)
    finally:
        try:
            cursor.close()
            connection.close()
        except Exception:
            pass

    # Stash for download endpoints
    request.session['recon_reconciled'] = reconciled
    request.session['recon_unreconciled'] = unreconciled

    response = {
        'message': f'Reconciliation completed. {len(reconciled)} matched, {len(unreconciled)} unmatched.',
        'reconciled_count': len(reconciled),
        'unreconciled_count': len(unreconciled),
        'download_reconciled_url': '/recon/download/reconciled/',
        'download_unreconciled_url': '/recon/download/unreconciled/',
    }
    return JsonResponse(response)

def reset_recon(request):
    """
    Clear reconciliation-related session data so the page can start fresh.
    """
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    for key in ['recon_dataset', 'recon_headers', 'recon_payload']:
        try:
            del request.session[key]
        except KeyError:
            continue
    for key in ['recon_reconciled', 'recon_unreconciled']:
        try:
            del request.session[key]
        except KeyError:
            continue

    return JsonResponse({'message': 'Reconciliation session cleared.'})

def _parse_recon_mapping(request):
    """
    Extract mapping from POST data and validate required selections.
    """
    mapping = {
        'Date': request.POST.get('Date'),
        'Amount': request.POST.get('Amount'),
        'AccountNo': request.POST.get('AccountNo'),
        'Description': request.POST.get('Description'),
        'RefNo': request.POST.get('RefNo'),
    }

    missing_fields = [field for field, source in mapping.items() if not source]
    if missing_fields:
        return mapping, JsonResponse({'message': f'Mapping missing for: {", ".join(missing_fields)}'}, status=400)

    return mapping, None

def _apply_recon_mapping(recon_records, mapping):
    """
    Apply mapping to session records and return list of mapped dicts.
    """
    mapped_records = []
    for row in recon_records:
        mapped_records.append({
            'Date': row.get(mapping['Date'], ''),
            'Amount': row.get(mapping['Amount'], ''),
            'AccountNo': row.get(mapping['AccountNo'], ''),
            'Description': row.get(mapping['Description'], ''),
            'RefNo': row.get(mapping['RefNo'], ''),
        })
    return mapped_records

def download_reconciled(request):
    """
    Download reconciled records as CSV.
    """
    data = request.session.get('recon_reconciled', [])
    return _records_to_csv_response(data, filename='reconciled.csv')

def download_unreconciled(request):
    """
    Download unreconciled records as CSV.
    """
    data = request.session.get('recon_unreconciled', [])
    return _records_to_csv_response(data, filename='unreconciled.csv')

def _records_to_csv_response(records, filename):
    """
    Convert list of dicts to CSV HttpResponse.
    """
    if not records:
        return HttpResponse('No data available', status=204)

    df = pd.DataFrame(records)
    # Ensure deterministic column order: mapped fields + status + any extras
    preferred_order = ['Date', 'Amount', 'AccountNo', 'Description', 'RefNo', 'ReconcileStatus']
    columns = [col for col in preferred_order if col in df.columns] + [col for col in df.columns if col not in preferred_order]
    df = df[columns]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    df.to_csv(response, index=False)
    return response

def normalize_date(value):
    """
    Normalize date-like values to YYYY-MM-DD for DB comparison.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    parsed = parse_date(str(value))
    if parsed:
        return parsed.strftime('%Y-%m-%d')
    try:
        parsed_ts = pd.to_datetime(value, errors='coerce')
        if not pd.isna(parsed_ts):
            return parsed_ts.strftime('%Y-%m-%d')
    except Exception:
        return None
    return None

def normalize_amount(value):
    """
    Normalize amount to a decimal string; returns None if parsing fails.
    """
    try:
        num = pd.to_numeric(value, errors='coerce')
        if pd.isna(num):
            return None
        return str(num)
    except Exception:
        try:
            return str(float(value))
        except Exception:
            return None

@csrf_exempt
def post_session_data(request):
    # Retrieve data from session
    file_type = request.POST.get('file_type', 'transactionsfile')
    uploaded_datasets = request.session.get('uploaded_datasets', {})
    uploaded_headers = request.session.get('uploaded_headers', {})

    legacy_details = request.session.get('file_details', [])
    legacy_headers = request.session.get('headers', [])

    file_details = uploaded_datasets.get(file_type, legacy_details)
    headers = uploaded_headers.get(file_type, legacy_headers)

    first_record = FileProcessSetting.objects.first()

    if first_record:
        endpoint_address = first_record.EndpointAddress
        invalid_account_ledger = first_record.InvalidAccountLedger
        endpoint_address2 = first_record.EndpointAddress2
        DefaultOD = first_record.DefaultODProduct
    
    if file_details:
        try:
            print(file_type,'-posting')

            if file_type == 'transactionsfile':
                

                # Convert file_details (list of dicts) to DataFrame
                dataset = pd.DataFrame(file_details)
                
                # Add BatchId column (e.g., using a UUID or timestamp)
                batch_id = f"batch_{uuid.uuid4().hex[:8]}"  # Unique batch ID
                dataset['BatchId'] = batch_id
                dataset['CoreBatchId'] = ""
                
                print('Starting Posting')
                # Initialize SOAP client
                wsdl = endpoint_address2
                client = zeep.Client(wsdl=wsdl)
                XMLTransactionBatch=""  # Initialize XMLTransactionBatch if needed
                root = ET.Element("Transactions")

                # Loop and validate accounts
                for index, row in dataset.iterrows():

                    transaction = ET.SubElement(root, "Transaction")
                    ET.SubElement(transaction, "TrxBranchId").text = str(row.get('Branch ID', 'N/A'))
                    ET.SubElement(transaction, "FromAccountId").text = str(row.get('AccountID', 'N/A'))

                    if(str(row.get('Account Type', 'N/A'))=='G'):
                        ET.SubElement(transaction, "FromAccountType").text = 'GL'
                    else:   
                        ET.SubElement(transaction, "FromAccountType").text = str(row.get('Account Type', 'N/A'))   

                    ET.SubElement(transaction, "Amount").text = str(row.get('Amount', '0.00'))
                    ET.SubElement(transaction, "Currency").text = str(row.get('Currency', 'KES'))  # Default if missing
                    ET.SubElement(transaction, "Description").text = str(row.get('Remarks', '') + ' ' + batch_id)
                    ET.SubElement(transaction, "Reference").text = str(row.get('BatchId', batch_id))
                    ET.SubElement(transaction, "Status").text = str(row.get('Status', 'N/A'))
                    ET.SubElement(transaction, "BatchId").text = batch_id
                    if(str(row.get('TrxType', 'N/A'))=='D'):
                        ET.SubElement(transaction, "TrxType").text = 'TD'
                    else:   
                        ET.SubElement(transaction, "TrxType").text = 'TC'
                
        
                XMLTransactionBatch = ET.tostring(root, encoding='unicode', method='xml')
                try:
                    clientText = client.service.RequestBatchTransferServiceTransaction(str(XMLTransactionBatch))
                    clientTextData = str(clientText)
                    
                    # Extract TransactionStatus1
                    statusstart = clientTextData.index("<TransactionStatus1>")
                    statusend = clientTextData.index("</TransactionStatus1>")
                    statusbatch = clientTextData.index("<TransactionStatus5>")
                    statusbatch = clientTextData.index("</TransactionStatus5>")
                    trxStatus = clientTextData[statusstart+20:statusend]
                    trxbatch = clientTextData[statusbatch+20:statusbatch]

                    response = {
                        'login_status':'valid', # response message
                        'FileStatus': trxStatus,
                        'FileBatch': trxbatch
                    }

                except zeep.exceptions.Fault as fault:
                    response = {
                        'login_status':'invalid', # response message
                        'FileStatus': False,
                        'FileBatch': "",
                        'message': str(fault)
                    }
                
                except Exception as e:
                    response = {
                        'login_status':'invalid', # response message
                        'FileStatus': False,
                        'FileBatch': "",
                        'message': str(e)
                    }

                return JsonResponse(response)
            elif file_type in ['ovewrdraftfile']:
                # Implement posting logic for other file types as needed
                # For now, just return a placeholder response
                dataset = pd.DataFrame(file_details)
                wsdl = endpoint_address
                client = zeep.Client(wsdl=wsdl)

                for index, row in dataset.iterrows():
                    customername1 = str(row.get('CustomerID', 'N/A'))
                    customername2 = str(row.get('', 'N/A'))
                    customername3 = str(row.get('', 'N/A'))
                    NATIONALID = str(row.get('CustomerIDCustomerID', 'N/A'))
                    MNo = str(row.get('CustomerPhoneNo', 'N/A'))
                    email = str(row.get('', 'N/A'))
                    amount = str(row.get('New Limit', '0'))

                    print('Creating Overdraft for CustomerID:', customername1, ' NationalID:', NATIONALID, ' MobileNumber:', MNo)
                    clientText = client.service.ODLimit(
                            '1003',
                            '01',
                            MNo,
                            customername1,
                            customername2,
                            customername3,
                            NATIONALID,
                            amount,
                            '',
                            DefaultOD
                        )
                    client_text_data = str(clientText)
                    print(client_text_data)
                
                response = {
                        'login_status':'valid', # response message
                        'FileStatus': trxStatus,
                        'FileBatch': trxbatch
                }

                return JsonResponse(response)
            
            else:
                response = {
                        'login_status':'invalid', # response message
                        'FileStatus': False,
                        'FileBatch': "",
                        'message': f'Posting not implemented for {UPLOAD_TYPE_LABELS.get(file_type, "the selected file type")}.'
                    }

                return JsonResponse(response)

        
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            response = {
                    'login_status':'invalid', # response message
                     'FileStatus': False,
                    'FileBatch': "",
                    'message': str(e)
                }

            return JsonResponse(response)
    else:
        response = {
                    'login_status':'invalid', # response message
                    'FileStatus': False,
                    'FileBatch': "",
                    'message': f'No session data available for {UPLOAD_TYPE_LABELS.get(file_type, "the selected file type")}.'
                }

        return JsonResponse(response)


def process_uploaded_file(uploaded_file):
    """
    Process uploaded file and return a pandas DataFrame
    Supports CSV, Excel, JSON, and PDF (via marker-pdf OCR), with all columns as strings.
    """
    # Get file extension
    file_name = uploaded_file.name
    file_extension = file_name.split('.')[-1].lower()
    
    # Read file based on extension
    if file_extension == 'csv':
        dataset = pd.read_csv(uploaded_file, dtype=str)
    elif file_extension in ['xls', 'xlsx']:
        dataset = pd.read_excel(uploaded_file, dtype=str)
    elif file_extension == 'json':
        dataset = pd.read_json(uploaded_file, dtype=str)
    elif file_extension == 'pdf':
        dataset = process_pdf_with_marker(uploaded_file)
    else:
        raise ValueError(f'Unsupported file format: {file_extension}')
    
    return dataset

def process_pdf_with_marker(uploaded_file):
    """
    Use marker-pdf (with OCR) to convert a PDF into a pandas DataFrame.
    Extracts the first readable table from the generated markdown;
    falls back to a single-column DataFrame of text lines when tables are missing.
    """
    try:
        from marker.convert import convert_single_pdf
        from marker.pdf import OCRProcessor
    except Exception as e:
        raise ValueError(
            f"marker-pdf is required for PDF/OCR processing. Install with `pip install marker-pdf[ocr]`: {e}"
        )

    # marker-pdf expects a file path; write uploaded chunks to a temp file.
    with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        # OCRProcessor will handle scanned PDFs; convert_single_pdf returns markdown text.
        ocr = OCRProcessor()
        try:
            markdown_text = convert_single_pdf(tmp_path, ocr=ocr)
        except TypeError:
            # Older versions may not support explicit OCR argument.
            markdown_text = convert_single_pdf(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    df = parse_markdown_tables(markdown_text)
    if df is not None and not df.empty:
        return df.astype(str)

    # Fallback: return text lines to keep pipeline working (mapping can point to these).
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip()]
    return pd.DataFrame({'Text': lines})

def parse_markdown_tables(markdown_text: str):
    """
    Parse markdown tables into a DataFrame.
    Returns the first non-empty table found, otherwise None.
    """
    if not markdown_text:
        return None

    tables = []
    blocks = markdown_text.split('\n\n')
    for block in blocks:
        if '|' not in block or block.count('|') < 4:
            continue
        try:
            # read_csv on pipe delimiter; drop empty edge columns commonly produced by markdown tables
            raw = pd.read_csv(StringIO(block), sep='|', engine='python')
            if raw.shape[1] > 2:
                raw = raw.drop(raw.columns[[0, -1]], axis=1)
            # Drop separator rows like --- | ---
            cleaned = raw[~raw.apply(lambda row: all(str(cell).strip('-: ') == '' for cell in row), axis=1)]
            if not cleaned.empty:
                tables.append(cleaned.reset_index(drop=True))
        except Exception:
            continue

    return tables[0] if tables else None


def connect_to_mysql(host, port, database, username, password):
    """
    Establish a connection to MySQL database
    
    Returns:
        connection: MySQL connection object
    """
    try:
        print('Lets Connect:'+host,port,database,username,password)
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=username,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor,
            ssl=False  # Disable SSL
        )
        print(f"Successfully connected to MySQL database: {database} at {host}:{port}")
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e} : {database} at {host}:{port}")
        return None
