import xml.etree.ElementTree as ET
import csvkit
import StringIO
import argparse

class LocalisationString(object):
	def __init__(self, dictionary = None):
		if dictionary == None:
			self.identifier = None
			self.language = None
			self.file = None
			self.text = None
			self.note = None
		else:
			self.identifier = dictionary["identifier"]
			self.language = dictionary["language"]
			self.file = dictionary["file"]
			self.text = dictionary["text"]
			self.note = dictionary["note"]

	def dictionary_representation(self):
		return {
			"identifier":self.identifier,
			"language":self.language,
			"file":self.file,
			"text":self.text,
			"note":self.note
		}
		
	def sorted_keys(self):
		return [
			"identifier",
			"file",
			"language",
			"note",
			"text",
		]
		
	def __repr__(self):
		return "<LocalisationString '%s' => '%s'>\r\n" % (self.identifier,self.text)

class XLIFFReader(object):
	
	def __init__(self,buf=None):
		self.root = ET.fromstring(buf)
	
	# Get the all of the translation strings
	def getLocalisationStrings(self):
		strings = []
		
		for file in self.root.getchildren():
			for element in file.getchildren():
				if "body" in element.tag:

					for unit in element.getchildren():						
						obj = LocalisationString()
						obj.file = file.attrib["original"]
						obj.language = file.attrib["source-language"]
						
						obj.identifier =  unit.attrib["id"]
						
						for child in unit.getchildren():
							if "source" in child.tag:
								obj.text = child.text
							elif "note" in child.tag:
								obj.note = child.text
								
						strings.append(obj)
						
		return strings
		
class XLIFFWriter(object):
	def __init__(self, localisedStrings):
		self.localisedStrings = localisedStrings
		
	def __rootElement__(self):
		ele = ET.Element("xliff")
		
		ele.attrib["version"] = "1.2"
		ele.attrib["xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
		ele.attrib["xmlns"] = "urn:oasis:names:tc:xliff:document:1.2"
		ele.attrib["xsi:schemaLocation"] = "urn:oasis:names:tc:xliff:document:1.2 http://docs.oasis-open.org/xliff/v1.2/os/xliff-core-1.2-strict.xsd"
		
		return ele
		
		
	def localizeTemplate(self):
		root = self.__rootElement__()
		
		fileBodies = {}
		
		for localisedString in self.localisedStrings:
			
			fileBody = None
			
			if localisedString.file in fileBodies:
				fileBody = fileBodies[localisedString.file]
			else:
				# Create a file
				file = ET.Element("file")
				file.attrib["original"] = localisedString.file
				file.attrib["source-language"] = localisedString.language
				file.attrib["datatype"] = "plaintext"
				root.append(file)
				
				header = ET.Element("header")
				file.append(header)
				
				body = ET.Element("body")
				file.append(body)
				
				fileBodies[localisedString.file] = body
				fileBody = body
				
			unit = ET.Element("trans-unit")
			
			unit.attrib["id"] = localisedString.identifier
			source = ET.Element("source")
			source.text = localisedString.text
			unit.append(source)
			note = ET.Element("note")
			note.text = localisedString.note
			unit.append(note)
			
			fileBody.append(unit)

		tree = ET.ElementTree(root)
		
		buf = StringIO.StringIO()
		
		tree.write(buf,xml_declaration=True,encoding="utf-8")
			
		return buf.getvalue()
		

class CSVReader(object):
	def __init__(self, fileObject = None):
		self.CSV = csvkit.DictReader(fileObject)
		
	def getLocalisationStrings(self):
		strings = []
		
		for row in self.CSV:
			strings.append(LocalisationString(row))
		
		# Sort by file
		def sortClosure(obj):
			return obj.file
			
		strings.sort(key=sortClosure)
			
		return strings

class CSVWriter(object):
	def __init__(self, localisedStrings = None):
		self.localisedStrings = localisedStrings
		
	def getCSV(self):
		buf = StringIO.StringIO()
		
		output = csvkit.DictWriter(buf,LocalisationString().sorted_keys())
		
		output.writeheader()
		for localisedString in self.localisedStrings:
			output.writerow(localisedString.dictionary_representation())
		
		return buf.getvalue()
	
def applyISOCode(localisedStrings,iso_code):
	if iso_code != None:
		for e in localisedStrings:
			e.language = iso_code
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description="XLIFF to CSV tool"
	)
	
	parser.add_argument("--mode", type = int, help="Mode of operation, CSV -> XLIFF or XLIFF -> CSV")
	parser.add_argument("--input", type = argparse.FileType('r', 0), help="Source file (CSV or XLIFF)")
	parser.add_argument("--output", nargs = "?", type = argparse.FileType('w ', 0), help="Destination file (CSV or XLIFF), this file is overwritten, not appended")
	parser.add_argument("--iso_code", nargs = "?", type = str, help="The two letter language ISO code for the output file, ie en, zh.")

	args = parser.parse_args()
	# args = parser.parse_args("--mode 1 --input es.xliff --output es.csv".split())
	# args = parser.parse_args("--mode 2 --input es.csv --output fr.xliff --iso_code fr".split())
	
	if args.mode == 1:
		xmlString = args.input.read()
		localisedStrings = XLIFFReader(xmlString).getLocalisationStrings()
		
		applyISOCode(localisedStrings,args.iso_code)
		
		csvString = CSVWriter(localisedStrings).getCSV()
		args.output.write(csvString)
		
	elif args.mode == 2: 
		localisedStrings = CSVReader(args.input).getLocalisationStrings()
		
		applyISOCode(localisedStrings,args.iso_code)
		
		xmlFile = XLIFFWriter(localisedStrings).localizeTemplate()
		
		args.output.write(xmlFile)
