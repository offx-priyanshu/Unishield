import csv
from io import StringIO
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
