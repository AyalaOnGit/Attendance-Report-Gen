import argparse
import logging
import os
from ocr_engine import get_pdf_text_and_layout
from classifier import identify_report_type
from parser_factory import create_parser
from transformation import (
    TransformationService,
    TypeATransformationStrategy,
    TypeBTransformationStrategy,
    ValidatingStrategyDecorator,
)
from exporters import export_results

DEFAULT_INPUT_DIR = 'data/inputs'
DEFAULT_OUTPUT_DIR = 'data/outputs'

logger = logging.getLogger('reportgen')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.handlers = [handler]


def parse_args():
    parser = argparse.ArgumentParser(
        description='Process attendance PDFs and render modified reports.'
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        default=DEFAULT_INPUT_DIR,
        help='Input PDF file or directory',
    )
    parser.add_argument(
        '-o',
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help='Directory for rendered output files',
    )
    return parser.parse_args()


def create_transformation_service():
    strategy_registry = {
        'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy()),
        'TYPE_B': ValidatingStrategyDecorator(TypeBTransformationStrategy()),
    }
    return TransformationService(strategy_registry)


def log_processing_error(file_name: str, message: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    error_log = os.path.join(output_dir, 'processing_errors.log')
    with open(error_log, 'a', encoding='utf-8') as out_file:
        out_file.write(f'{file_name}: {message}\n')


def process_file(file_path: str, output_dir: str, transformation_service):
    file_name = os.path.basename(file_path)
    print(f'--- Processing: {file_name} ---')

    try:
        raw_text, layout = get_pdf_text_and_layout(file_path)
        if not raw_text.strip() and not layout:
            raise ValueError('OCR returned no usable text or layout for this file.')

        report_type = identify_report_type(raw_text)
        parser = create_parser(report_type, raw_text, layout)
        report = parser.parse()

        if not report.rows:
            raise ValueError('No attendance rows found. OCR or parser did not detect expected data.')

        modified_report = transformation_service.transform_report(report_type, report)
        base_name = os.path.splitext(file_name)[0] + '_NEW'
        export_results(modified_report, base_name, output_dir)
        employee_name = report.employee_name or 'לא זוהה'
        print(f"Successfully created outputs for {file_name} (Employee: {employee_name})")

    except Exception as exc:
        message = str(exc)
        logger.error(f'Failed processing {file_name}: {message}')
        log_processing_error(file_name, message, output_dir)


def resolve_input_path(input_path: str) -> str:
    if os.path.exists(input_path):
        return input_path

    container_default = '/data'
    if os.path.isdir(container_default):
        logger.warning(
            'Input path not found; falling back to mounted /data directory for container execution.'
        )
        return container_default

    return input_path


def main():
    args = parse_args()
    transformation_service = create_transformation_service()
    output_dir = args.output_dir or DEFAULT_OUTPUT_DIR
    input_path = resolve_input_path(args.input_path)

    if os.path.isdir(input_path):
        pdf_files = [
            name for name in sorted(os.listdir(input_path)) if name.lower().endswith('.pdf')
        ]
        if not pdf_files:
            logger.warning(
                f'No PDF files found in input directory: {input_path}'
            )
            return

        for file_name in pdf_files:
            process_file(os.path.join(input_path, file_name), output_dir, transformation_service)

    elif os.path.isfile(input_path):
        process_file(input_path, output_dir, transformation_service)

    else:
        logger.error(f"Error: Input path '{input_path}' does not exist.")


if __name__ == '__main__':
    main()
