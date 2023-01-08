#! /usr/bin/env/python 3.0
#
# Running this script will update files that are used when all of the test
# cases are compiled into a single .war file.
#

import sys,os,re

# add parent directory to search path so we can use py_common
sys.path.append("..")

import py_common

def build_list_of_java_testcase_files(directory):

	files_to_check = []
	for root, dirs, files in os.walk(directory):
		for name in files:
			result = re.search(py_common.get_primary_testcase_filename_regex(), name, re.IGNORECASE)

			if result != None:
				files_to_check.append(os.path.realpath(os.path.join(root,name)))

		# don't enumerate files in .svn dirs
		if '.svn' in dirs: 
			dirs.remove('.svn')

		# don't enumerate files in support directories
		if 'testcasesupport' in dirs:
			dirs.remove('testcasesupport')

	return files_to_check

def update_file(file_path, file, tag_start, tag_end, lines):

	full_file_path = os.path.join(file_path, file)
	file_contents = py_common.open_file_and_get_contents(full_file_path)

	# get contents from start of file up to tag, get contents from end tag
	# to EOF
	up_to_tag_start = file_contents.split(tag_start)[0]
	tag_end_to_eof = file_contents.split(tag_end)[1]

	auto_gen_content = "\n".join(lines)

	# re-build the file with the modified content between the tags
	modified_file_contents = up_to_tag_start + \
			tag_start + "\n" + \
			auto_gen_content + "\n" + \
			"\t\t\t" + tag_end + \
			tag_end_to_eof

	# write out the new file
	outfile = os.path.join(file_path, file)
	py_common.write_file(outfile, modified_file_contents)

def generate_web_xml_entry(namespace, classname):

	entry = []

	entry.append("\t<servlet>")
	entry.append("\t\t<description/>")
	entry.append("\t\t<display-name>" + classname + "</display-name>")
	entry.append("\t\t<servlet-name>" + classname + "</servlet-name>")
	entry.append("\t\t<servlet-class>" + namespace + classname + "</servlet-class>")
	entry.append("\t</servlet>")
	entry.append("\t<servlet-mapping>")
	entry.append("\t\t<servlet-name>" + classname + "</servlet-name>")
	entry.append("\t\t<url-pattern>" + classname + "</url-pattern>")
	entry.append("\t</servlet-mapping>")

	return entry

def update_package_name(file, package):

	lines = py_common.open_file_and_get_lines(file)
	lines.pop(0)
	lines.insert(0, "package " + package + ";\n")
	py_common.write_file(file, "".join(lines))
	
# Main.java has 9 separate locations where we need to replace text due to 
#  us running into the Java classfile limit on the length of a method (64K of 
#  bytecode)
def update_Main_java(file_path, non_servlet_testcase_lines, package):
	# tags for Main.java that indicate where to replace text
	main_dot_java = "Main.java";
	auto_gen_tag_start = "/* BEGIN-AUTOGENERATED-JAVA-TESTS-X */"
	auto_gen_tag_end = "/* END-AUTOGENERATED-JAVA-TESTS-X */"
	for i in range(1,10):
	
		# replace the X in the tags with the current number
		current_auto_gen_tag_start = auto_gen_tag_start.replace("X", str(i))
		current_auto_gen_tag_end = auto_gen_tag_end.replace("X", str(i))
	
		# filter non_servlet_testcase_lines to just ones for CWE1, CWE2, etc
		test = re.compile("CWE"+str(i))
		#current_non_servlet_testcase_lines = filter(test.search,non_servlet_testcase_lines) 
		
		current_non_servlet_testcase_lines = [f for f in non_servlet_testcase_lines if test.search(f)] 
		
		# call update-file
		update_file(file_path, main_dot_java, current_auto_gen_tag_start, current_auto_gen_tag_end, current_non_servlet_testcase_lines)
		
	# replace package name with the correct package
	update_package_name(os.path.join(file_path, main_dot_java), package)
	
# ServletMain.java has 9 separate locations where we need to replace text due to 
#  us running into the Java classfile limit on the length of a method (64K of 
#  bytecode)
def update_Servlet_Main_java(file_path, servlet_testcase_lines, package):
	# tags for Main.java that indicate where to replace text
	servlet_main_dot_java = "ServletMain.java";
	auto_gen_tag_start = "/* BEGIN-AUTOGENERATED-SERVLET-TESTS-X */"	
	auto_gen_tag_end = "/* END-AUTOGENERATED-SERVLET-TESTS-X */"
	for i in range(1,10):
	
		# replace the X in the tags with the current number
		current_auto_gen_tag_start = auto_gen_tag_start.replace("X", str(i))
		current_auto_gen_tag_end = auto_gen_tag_end.replace("X", str(i))
	
		# filter non_servlet_testcase_lines to just ones for CWE1, CWE2, etc
		test = re.compile("CWE"+str(i))
		#current_non_servlet_testcase_lines = filter(test.search,non_servlet_testcase_lines) 
		
		current_servlet_testcase_lines = [f for f in servlet_testcase_lines if test.search(f)] 
		
		# call update-file
		update_file(file_path, servlet_main_dot_java, current_auto_gen_tag_start, current_auto_gen_tag_end, current_servlet_testcase_lines)
		
	# replace package name with the correct package
	update_package_name(os.path.join(file_path, servlet_main_dot_java), package)
		
def update_Main_java_ServletMain_java_and_web_xml(testcase_location=".", main_path="src\\testcasesupport\\", web_path="WebContent\\WEB-INF\\"):	

	# get list of testcase files
	testcase_files = build_list_of_java_testcase_files(testcase_location)

	# build up the class instantiation lines
	non_servlet_testcase_lines = []
	servlet_testcase_lines = []
	web_lines = []
	namespace = ""
	for fullfilepath in testcase_files:

		filename = os.path.basename(fullfilepath)

		# figure out the namespace based on the file path
		tc_index = fullfilepath.index("src\\testcases")
		f_index = fullfilepath.index(filename)
		namespace = "testcases" + fullfilepath[tc_index + len("src\\testcases"):f_index].replace("\\", ".")

		# remove .java from the end of the filename to get the classname
		classname = filename[:-5]

		# there are 2 types of testcases; if the class extends AbstractTestCaseServlet,
		# then we want to put that in the ServletMain file;
		# otherwise, it goes in the normal Main file.
		#if "extends AbstractTestCaseServlet" in open_file_and_get_contents(fullfilepath):
		reServlet = re.compile("Servlet", re.IGNORECASE)
		if reServlet.search(classname) != None:
			line = "\t\t\t(new " + namespace + \
					classname + \
					"()).runTest(request, response);"

			servlet_testcase_lines.append(line)

			lines = generate_web_xml_entry(namespace, classname)
			web_lines.extend(lines)
		else:
			line = "\t\t\t(new " + namespace + \
					classname + \
					"()).runTest(\"" + classname + "\");"

			non_servlet_testcase_lines.append(line)

	servlet_main_dot_java = "ServletMain.java";
	web_xml = "web.xml"

	# tags for web.xml that indicate where to replace text
	auto_gen_tag_start_web = "<!-- BEGIN-AUTOGENERATED-SERVLETS -->"
	auto_gen_tag_end_web = "<!-- END-AUTOGENERATED-SERVLETS -->"
	
	package = namespace[:-1] # Remove the trailing .

	#update Main.java
	update_Main_java(main_path, non_servlet_testcase_lines, package)

	#updated ServletMain.java
	update_Servlet_Main_java(main_path, servlet_testcase_lines, package)

	#update web.xml
	update_file(web_path, web_xml, auto_gen_tag_start_web, auto_gen_tag_end_web, web_lines)

