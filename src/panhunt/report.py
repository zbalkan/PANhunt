import platform

from . import panutils
from .models import ScanResult


class ReportGenerator:
    """Formats a ScanResult into text or JSON. Pure logic — no file I/O."""

    @staticmethod
    def format_header(result: ScanResult) -> str:
        newline = '\n'
        sep = '=' * 100
        return (
            f'PAN Hunt Report - {result.start_time.strftime("%H:%M:%S %d/%m/%Y")}{newline}'
            f'{sep}{newline}'
            f'Searched {result.config.target_path}{newline}'
            f'Excluded {",".join(result.config.excluded_paths)}{newline}'
            f'Uname: {" | ".join(platform.uname())}{newline}'
            f'Elapsed time: {result.elapsed}{newline}'
            f'Found {result.pan_count} possible PANs.{newline}'
            f'Scan status: {result.status} ({len(result.interesting_files)} unprocessed/failed items){newline}'
            f'{sep}{newline}'
        )

    def generate_text(self, result: ScanResult) -> str:
        newline = '\n'
        report = self.format_header(result) + newline

        for file in result.matched_files:
            # size_friendly is called once per matched file by design — file size is part of the report spec.
            report += f'FOUND PANs: {file.abspath} ({panutils.size_friendly(file.size)}){newline}'
            for pan in file.matches:
                report += f'\t{pan}{newline}'
            report += newline

        if result.interesting_files:
            report += f'Interesting Files to check separately, probably a permission or file size issue:{newline}'
            for interesting in sorted(result.interesting_files, key=lambda x: x.basename):
                report += f'{interesting.abspath} ({panutils.size_friendly(interesting.size)}){newline}'
                report += f'Error: {interesting.errors}{newline}'

        return report

    def generate_json(self, result: ScanResult) -> dict:
        data: dict = {
            'timestamp': result.start_time.strftime('%H:%M:%S %d/%m/%Y'),
            'searched': result.config.target_path,
            'excluded': ','.join(result.config.excluded_paths),
            'elapsed': str(result.elapsed),
            'pans_found': result.pan_count,
            'scan_status': result.status,
            'exit_code': result.exit_code,
            'failed_items': len(result.interesting_files),
            'schema_version': '1.0.0',
            'findings': [
                {'path': finding.logical_path, 'brand': pan.brand,
                 'masked_pan': pan.masked, 'start': pan.start, 'end': pan.end,
                 'source_cursor': None}
                for finding in result.matched_files for pan in finding.matches
            ],
            'pans_found_results': {
                f.abspath: [str(pan) for pan in f.matches]
                for f in result.matched_files
            },
        }

        if result.interesting_files:
            data['interesting_files'] = {
                'total': len(result.interesting_files),
                'files': [
                    {'path': f.abspath, 'size': f.size, 'errors': f.errors}
                    for f in result.interesting_files
                ],
            }

        return data

    def generate_sarif(self, result: ScanResult) -> dict:
        """Produce SARIF 2.1.0 without exposing the unmasked card number."""
        items = []
        for finding in result.matched_files:
            for pan in finding.matches:
                region = {'charOffset': pan.start, 'charLength': pan.end - pan.start} if (
                    pan.start is not None and pan.end is not None) else None
                location = {'physicalLocation': {'artifactLocation': {'uri': finding.logical_path}}}
                if region is not None:
                    location['physicalLocation']['region'] = region
                items.append({'ruleId': 'PANHUNT001', 'level': 'warning',
                              'message': {'text': f'Possible {pan.brand} PAN: {pan.masked}'},
                              'locations': [location]})
        return {'version': '2.1.0', '$schema':
                'https://json.schemastore.org/sarif-2.1.0.json',
                'runs': [{'tool': {'driver': {'name': 'PANhunt',
                         'rules': [{'id': 'PANHUNT001', 'name': 'PaymentAccountNumber',
                                    'shortDescription': {'text': 'Possible payment card number'}}]}},
                          'results': items, 'properties': {'scanStatus': result.status,
                          'failedItems': len(result.interesting_files)}}]}
