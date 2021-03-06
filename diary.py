#!/usr/bin/python
import sys, os, datetime, glob, re, calendar
import dateutil.parser as parser
from subprocess import call

# Set this to something if you wish to use truecrypt
TRUECRYPT_VOLUME = ""
# If using truecrypt ensure this points to the truecrypt mounted folder
# Diary config file: Mine says '~/Dropbox/My Notes/'
DIARY_CONFIG_FILE = os.path.expanduser('~/.diary')
try:
	DIARY_CONFIG = map(str.strip, open(DIARY_CONFIG_FILE).readlines())
except IOError:
	DIARY_CONFIG = ['']
DIARY_FOLDER = os.path.expanduser(DIARY_CONFIG[0])
EDITOR = os.environ.get('EDITOR','vim')

ED_ENABLED = False
if len(EDITOR) > 0:
	ED_ENABLED = True

TRUECRYPT_ENABLED = False
if len(TRUECRYPT_VOLUME) > 0:
	TRUECRYPT_BINARY = os.popen("which truecrypt").read().rstrip('\n')
	if TRUECRYPT_BINARY != 0 and len(TRUECRYPT_BINARY) > 0:
		TRUECRYPT_ENABLED = True

NOW = datetime.datetime.now()

#Handles arguments a function calls
def main():
	if TRUECRYPT_ENABLED:
		mount_truecrypt()

	if not diary_folder_exists():
		print("Please specify a valid diary folder, using a config file at "
			  "~/.diary")
		return

	action = ''
	argument = ''

	if len(sys.argv) >= 2:
		action=sys.argv[1]
	if len(sys.argv) >= 3:
		argument=' '.join(sys.argv[2:])
	else:
		argument=None

	{'add': add,
			'ls': list,
			'cat' : cat,
			'find': d_search,
			'help': help,
			'hide': dismount_truecrypt,
			'edit': edit,
			'rand': random,
			'stats': stats,
			}.get(action, help)(argument)

def mount_truecrypt():
	if not diary_folder_exists():
		os.popen('%s %s' % (TRUECRYPT_BINARY, TRUECRYPT_VOLUME)).read()

def resolve_date(diary_date=None):
	if diary_date==None:
		date = datetime.date.today()
	elif isinstance(diary_date, datetime.datetime):
		date = diary_date
	elif isinstance(diary_date, str):
		dates = []
		for file in get_diary_files():
			try:
				dates.append(
					re.search(
						'Journal (\d\d\d\d-\d\d-\d\d).txt',
						os.path.basename(file)
					).groups()[0]
				)
			except AttributeError:  # no match
				pass

		if diary_date.startswith('yes'):
			date = datetime.date.today() - datetime.timedelta(days=1)
		elif diary_date.startswith('tom'):
			date = datetime.date.today() + datetime.timedelta(days=1)
		elif diary_date.startswith('tod'):
			date = datetime.date.today()
		elif diary_date.startswith('last'):
			files = get_diary_files()
			datestamp = dates[-1]
			try:
				date = parser.parse(datestamp)
			except ValueError:
				print('Invalid date format.')
				help()
				exit()
		elif (diary_date.isdigit()
				or (diary_date.startswith('-') and diary_date[1:].isdigit())
		):
			datestamp = dates[int(float(diary_date))]
			try:
				date = parser.parse(datestamp)
			except ValueError:
				print('Invalid date format.')
				help()
				exit()
		else:
			try:
				date = parser.parse(diary_date)
			except ValueError:
				print('Invalid date format.')
				help()
				exit()
	else:
		print('Invalid date format.')
		help()
		exit()

	return date.strftime("%Y-%m-%d")

def dismount_truecrypt(arg):
	if diary_folder_exists():
		os.popen('%s %s -d' % (TRUECRYPT_BINARY, TRUECRYPT_VOLUME))

#Add a diary entry via the text supplied
def add(text, diary_date=None):
	diary_date = resolve_date(diary_date)
	if text == None:
		text = ''

	abs_file = get_diary_folder() + 'Journal ' + diary_date + ".txt"
	stamp = datetime.datetime.now().strftime('%T')

	# Blank line if there are previous entries, otherwise none
	if os.path.isfile(abs_file):
		template = "\n{stamp}\n{content}"
	else:
		template = "{stamp}\n{content}"
	content = text + ("\n" if text else "")
	with open(abs_file, "a") as today:
		today.write(template.format(stamp=stamp, content=content))
	print("Added diary entry")
	return abs_file

def random(text):
	file_list = get_diary_files()
	from random import choice
	random_date = choice(file_list)
	if os.path.isfile(random_date):
		diary_file = open(random_date,'r').read()
		print(random_date)
		print(diary_file)
	else:
		print('No diary entry specified and no entries for today')

#Edit a diary entry via the text supplied
def edit(diary_date=None):
	diary_date = resolve_date(diary_date)

	abs_file = add(text=None, diary_date=diary_date)
	with open(abs_file, 'a') as today:
		today.write('\n')
	call([
		EDITOR,
		"+set syntax=markdown",
		"+set ft=markdown",
		"+9999999",
		'-c',
		'startinsert',
		abs_file
	])
	# call([EDITOR, abs_file])


#List a specific date or today
def cat(diary_date=None):
	"""List all elements for a specific date"""
	diary_date = resolve_date(diary_date)

	abs_file = get_diary_folder() + 'Journal ' + diary_date + ".txt"
	if os.path.isfile(abs_file):
		print(abs_file + "\n")
		diary_file = open(abs_file,'r').read()
		print(diary_file)
	else:
		print('No diary entry specified and no entries for today')

#Search all files for a supplied pattern
def d_search(pattern):
	pattern = pattern or str(raw_input('Find what: '))
	file_list = get_diary_files()
	for infile in file_list:
		file = open(infile,"r")
		text = file.read()
		file.close()
		index = text.find(pattern)
		if index > 0:
			search_file(infile, pattern, text)

#Build up stats by month and year
def stats(text):
	file_list = get_diary_files()
	ordered_list = {}
	for infile in file_list:
		infile_fullname = os.path.basename(infile)
		infile_name = os.path.splitext(infile_fullname)[0]
		# Only accommdates filenames like "<something> <date>.ext"
		datestr = infile_name.split(' ')[-1]
		try:
			date = parser.parse(datestr)
		except (TypeError, ValueError):
			print("Skipping because we didn't find a date in the filename: " +
					infile_name)
			continue
		file = open(infile,"r")
		text = file.read()
		tempwords = text.split(None)

		if date.year in ordered_list:
			if date.month in ordered_list[date.year]:
				ordered_list[date.year][date.month] += len(tempwords)
			else:
				ordered_list[date.year][date.month] = len(tempwords)
		else:
			ordered_list[date.year] = {}
			ordered_list[date.year][date.month] = len(tempwords)
	years = sorted(ordered_list.iteritems())
	print("Word Count By Month\n")
	for year in years:
		for month in year:
			if isinstance(month, int):
				print("%d" % month)
			elif isinstance(month, dict):
				for date, word_count in month.iteritems():
					print("%s" % calendar.month_abbr[date], word_count)

def list(argument):
	file_list = get_diary_files()
	for path in file_list:
		print(os.path.basename(path))
	print("Diary folder is " + get_diary_folder())


#Searches the specific file for text
def search_file(infile, pattern, text):
	file_name = infile.split('/')
	lines = text.split('\n')
	for line in lines:
		index = line.find(pattern)
		if index > 0:
			print ("%s -- %s" % (file_name[-1], line))

def get_diary_folder():
	if DIARY_FOLDER:
		if DIARY_FOLDER[-1] == '/':
			return DIARY_FOLDER
		return DIARY_FOLDER + '/'
	return False

def diary_folder_exists():
	if get_diary_folder() != False:
		return os.path.isdir(get_diary_folder())
	return False

def get_diary_files():
	file_list = glob.glob(os.path.join(get_diary_folder(), 'Journal *.txt'))
	file_list.sort()
	return file_list

def help(argument=None):
	print("Usage:")
	print("\tdiary.py add 'Today I went to the @shops and bought some cake for the #party'")
	print("\tdiary.py find 'search term'")
	print("\tdiary.py cat  - Prints current day or date format specified")
	print("\tdiary.py ls   - Lists all available entries")
	print("\tdiary.py help - Displays this text")
	print("\tdiary.py hide - Will unmount the truecrypt volume")
	print("\tdiary.py edit - Edits current day or date specified in format")
	print("\tdiary.py rand - Returns random element")
	print("\tdiary.py stats - Prints monthly word-count of stats")
	print("\tDates can be yesterday, today, tomorrow, last, or integer offset")

if __name__ == '__main__':
	main()
