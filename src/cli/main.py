import argparse
import logging
import os
from container import build_container, Container

DEFAULT_INPUT_DIR = 'data/inputs'
DEFAULT_OUTPUT_DIR = 'data/outputs'

logger = logging.getLogger('reportgen')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.handlers = [handler]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Process attendance PDFs and render modified reports.'
    )
    parser.add_argument(
        'input_path', nargs='?', default=DEFAULT_INPUT_DIR,
        help='Input PDF file or directory',
    )
    parser.add_argument(
        '-o', '--output-dir', default=DEFAULT_OUTPUT_DIR,
        help='Directory for rendered output files',
    )
    return parser.parse_args()


def log_processing_error(file_name: str, message: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'processing_errors.log'), 'a', encoding='utf-8') as f:
        f.write(f'{file_name}: {message}\n')


def process_file(file_path: str, output_dir: str, container: Container) -> None:
    file_name = os.path.basename(file_path)
    print(f'--- Processing: {file_name} ---')
    try:
        raw_text, layout = container.get_pdf_text_and_layout(file_path)
        if not raw_text.strip() and not layout:
            raise ValueError('OCR returned no usable text or layout for this file.')

        report_type = container.identify_report_type(raw_text)
        parser      = container.create_parser(report_type, raw_text, layout)
        report      = parser.parse()

        if not report.rows:
            raise ValueError('No attendance rows found.')

        modified = container.transformation_service.transform_report(report_type, report)
        base_name = os.path.splitext(file_name)[0] + '_NEW'
        container.export_results(modified, base_name, output_dir)
        print(f"Successfully created outputs for {file_name} (Employee: {report.employee_name or 'לא זוהה'})")

    except Exception as exc:
        logger.error('Failed processing %s: %s', file_name, exc)
        log_processing_error(file_name, str(exc), output_dir)


def resolve_input_path(input_path: str) -> str:
    if os.path.exists(input_path):
        return input_path
    container_default = '/data'
    if os.path.isdir(container_default):
        return container_default
    return input_path


def main() -> None:
    args = parse_args()
    container  = build_container()
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    input_path = resolve_input_path(args.input_path)

    if os.path.isdir(input_path):
        pdf_files = sorted(f for f in os.listdir(input_path) if f.lower().endswith('.pdf'))
        if not pdf_files:
            logger.warning('No PDF files found in: %s', input_path)
            return
        for file_name in pdf_files:
            process_file(os.path.join(input_path, file_name), output_dir, container)

    elif os.path.isfile(input_path):
        process_file(input_path, output_dir, container)

    else:
        logger.error("Input path '%s' does not exist.", input_path)


if __name__ == '__main__':
    main()
