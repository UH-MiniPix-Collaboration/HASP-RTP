from __future__ import print_function
import pickle
import os.path
import sys
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID = 'PUT_SHEET_ID_HERE'
WRITE_RANGE_NAME = 'Sheet1!D1:D1'

def createService():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if 'creds' not in os.listdir(os.getcwd()):
        os.makedirs(os.getcwd() + '/creds')
    if os.path.exists('creds/token.pickle'):
        with open('creds/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'creds/credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('creds/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('sheets', 'v4', credentials=creds)
    return service


def writeCell(command):
    service = createService()
    body = {
        'values': [[command]]
    }
    result = service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=WRITE_RANGE_NAME,
        valueInputOption='RAW', body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))


if __name__  == "__main__":
    try:
        if len(sys.argv) == 2:
            print ('args: ' + str(sys.argv))
            writeCell(str(sys.argv[1]))
        else:
            print("Incorrect arguments.")
    except Exception as e:
        print(e)
