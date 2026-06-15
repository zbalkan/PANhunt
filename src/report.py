import platform
import sys
import time

import panutils
from models import ScanResult


class ReportGenerator:
    """Formats a ScanResult into text or JSON. Pure logic — no file I/O."""

    def generate_text(self, result: ScanResult) -> str:
        newline = '\n'
        sep = '=' * 100
        report = (
            f'PAN Hunt Report - {time.strftime("%H:%M:%S %d/%m/%Y")}{newline}'
            f'{sep}{newline}'
            f'Searched {result.config.search_dir}{newline}'
            f'Excluded {",".join(result.config.excluded_directories)}{newline}'
            f'Command: {" ".join(sys.argv)}{newline}'
            f'Uname: {" | ".join(platform.uname())}{newline}'
            f'Elapsed time: {result.elapsed}{newline}'
            f'Found {result.pan_count} possible PANs.{newline}'
            f'{sep}{newline}{newline}'
        )

        for file in result.matched_files:
            report += f'FOUND PANs: {file.abspath}{newline}'
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
            'searched': result.config.search_dir,
            'excluded': ','.join(result.config.excluded_directories),
            'command': ' '.join(sys.argv),
            'elapsed': str(result.elapsed),
            'pans_found': result.pan_count,
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
