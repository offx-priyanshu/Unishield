import csv
import pandas as pd
from io import StringIO, BytesIO
from flask import make_response

class ExportService:
    @staticmethod
    def export_csv(headers, data, filename):
        """Generates a CSV file from data and headers."""
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(headers)
        cw.writerows(data)
        
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename={filename}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    @staticmethod
    def export_excel(headers, data, filename):
        """Generates an Excel (.xlsx) file using pandas."""
        df = pd.DataFrame(data, columns=headers)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='SNOX Manifest')
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
