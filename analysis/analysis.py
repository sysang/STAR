from argparse import ArgumentParser
from pathlib import Path
from typing import Text
import json
import logging
import os
import sys

PACKAGE_PATH = os.path.dirname(__file__)

parser = ArgumentParser()
parser.add_argument('-i', '--input-file', type=str, help='input file')
parser.add_argument('-ip', '--input-path', type=str, help='input path')
parser.add_argument('-op', '--output-path', type=str, help='output path')
parser.add_argument('-o', '--output-file', type=str, help='output file')
parser.add_argument('-a', '--action', type=str, help='action to be executed', required=True)
parser.add_argument('-t', '--threshold', type=int, default=2, help='threshold for UserGuide/instruct events')
parser.add_argument('-f', '--force-rewrite', action='store_true', help='force rewrite if exists')
parser.add_argument('-ll', '--log-level', type=str, default='INFO', help='logging level', choices=['CRITICAL', 'FATAL',
																								   'ERROR', 'WARNING',
																								   'WARN', 'INFO',
																								   'DEBUG'])


def find_mislabelled_dialogues_unhappy_as_happy(input_path: Text, output_file: Text, threshold: int):
	problematic_files = set()
	path = Path(input_path)

	for f in path.glob('*.json'):
		with f.open() as in_file:
			data = json.load(in_file)
		if data['CompletionLevel'] != 'Complete':
			logging.debug(f'Skipping {f} as CompletionLevel="{data["CompletionLevel"]}"!')
			continue

		# Extract dialogue type key (either "happy", "unhappy", or "multitask")
		if data['Scenario']['Happy']:
			type_key = 'happy'
		else:
			if data['Scenario']['MultiTask']:
				type_key = 'multitask'
			else:
				type_key = 'unhappy'
		logging.info(f'Extracted type_key="{type_key}".')

		num_user_guide_instruct_events = 0
		for event in data['Events']:
			agent_is_user_guide = event['Agent'] == 'UserGuide'
			action_is_instruct = event['Action'] == 'instruct'
			dialogue_is_happy = type_key == 'happy'

			if dialogue_is_happy and (agent_is_user_guide or action_is_instruct):
				num_user_guide_instruct_events += 1

		logging.debug(f'Encountered {num_user_guide_instruct_events} UserGuide/instruct events in {f}.')
		if num_user_guide_instruct_events > threshold:
			problematic_files.add(f.name)

	logging.info(f'Found {len(problematic_files)} potentially mislabelled files!')
	logging.info(f'Writing list of files to {output_file}...')
	with open(output_file, 'w') as out_file:
		out_file.write('\n'.join(problematic_files))
	logging.info(f'Finished!')


if __name__ == '__main__':
	args = parser.parse_args()

	log_formatter = logging.Formatter(fmt='%(asctime)s: %(levelname)s - %(message)s', datefmt='[%d/%m/%Y %H:%M:%S %p]')
	root_logger = logging.getLogger()
	root_logger.setLevel(getattr(logging, args.log_level))

	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setFormatter(log_formatter)
	root_logger.addHandler(console_handler)

	if args.output_path is not None and not os.path.exists(args.output_path):
		os.makedirs(args.output_path)

	if args.action == 'find_mislabelled_dialogues_unhappy_as_happy':
		if args.force_rewrite or not os.path.exists(os.path.join(args.output_path, args.output_file)):
			find_mislabelled_dialogues_unhappy_as_happy(input_path=args.input_path, threshold=args.threshold,
														output_file=os.path.join(args.output_path, args.output_file))
		else:
			logging.info(f'{args.output_file} already exists at {args.output_path}, skipping!')
	else:
		raise ValueError(f'Action "{args.action}" not supported!')