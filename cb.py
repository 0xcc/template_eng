#-*- coding:utf-8 -*-

class CodeBuilder(object):
	INDENT_STEP=4

	def __init__(self,indent=0):
		self.indent=indent 	#当前缩进
		self.lines=[]		#保存代码

	def forward(self):
		self.indent+=self.INDENT_STEP #缩进向前进一步

	def backward(self):
		self.indent-=self.INDENT_STEP #缩进后退一步

	def add(self,code):
		self.lines.append(code)

	def add_line(self,code):
		#拼接缩进后的代码
		self.lines.append(' '*self.indent+code)

	def __str__(self):
		#for i in self.lines:
		#	print i
		return '\n'.join(map(str,self.lines))

	def __repr__(self):
		return str(self)


