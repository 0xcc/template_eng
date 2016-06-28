#-*- coding:utf-8 -*-
from cb import CodeBuilder
import re
import os
class Template(object):
	def __init__(self,raw_text,indent=0,default_context=None,
					func_name='__func_name',result_var='__result',
					template_dir='templates',encoding='utf-8'):
		self.raw_text=raw_text
		self.default_context=default_context or {}
		self.func_name=func_name
		self.result_var=result_var
		self.code_builder=code_builder=CodeBuilder(indent=indent)
		self.buffered=[]
		self.template_dir=template_dir
		self.encoding=encoding

		#变量{{ abc }}
		self.re_variable=re.compile(r'\{\{.*?\}\}')
		#注释 {#...#}
		self.re_comment=re.compile(r'\{#.*?#\}')
		#标签 {% if elif else for break %}
		self.re_tag=re.compile(r'\{%.*?%\}')

		self.handlers=(
						(self.re_variable.match,self._handle_variable),
						(self.re_comment.match,self._handle_comment),
						(self.re_tag.match,self._handle_tag),
						)
		self.default_handler=self._handle_string

		#分组
		self.re_tokens=re.compile(r'''(\{\{.*?\}\})|(\{#.*?#\})|(\{%.*?%\})''')

		# extends base.html
		self.re_extends=re.compile(r'\{% extends (?P<name>.*?) %\}')
		# blocks
		'''
			{% block xyz %}
			html and template code
			{% endblock  %}
		'''
		self.re_blocks = re.compile(
			r'\{% block (?P<name>\w+) %\}'
			r'(?P<code>.*?)'
			r'\{% endblock \1 %\}', re.DOTALL)

		# block.super
		#{{ block.super}}
		self.re_block_super=re.compile(r'\{\{ block\.super \}\}')


		#def __func_name():
		code_builder.add_line('def {}():'.format(self.func_name))
		code_builder.forward()
		#__result=[]
		code_builder.add_line('{}=[]'.format(self.result_var))
		self._parse_text()

		#中间
		self.flush_buffer()

		#尾部 
		code_builder.add_line('return "".join({})'.format(self.result_var))
		code_builder.backward()

	def _handle_variable(self,token):
		variable =token.strip('{} ')
		self.buffered.append('str({})'.format(variable))

	def _handle_comment(self,token):
		pass

	def _handle_string(self,token):
		self.buffered.append('{}'.format(repr(token)))

	def _handle_tag(self,token):
		self.flush_buffer()
		tag=token.strip('{%} ')
		tag_name=tag.split()[0]
		if tag_name=='include':
			self._handle_include(tag,tag_name)
		else:
			self._handle_statement(tag,tag_name)

	def _handle_statement(self,tag,tag_name):
		#print "tag: ",tag
		#print "tag_name: ",tag_name
		if tag_name in ('if', 'elif', 'else', 'for'):
			# elif 和 else 之前需要向后缩进一步
			if tag_name in ('elif', 'else'):
				self.code_builder.backward()
			# if True:, elif True:, else:, for xx in yy:
			self.code_builder.add_line('{}:'.format(tag))
			# if/for 表达式部分结束，向前缩进一步，为下一行做准备
			self.code_builder.forward()
		elif tag_name in ('break',):
			self.code_builder.add_line(tag)
		elif tag_name in ('endif', 'endfor'):
			# if/for 结束，向后缩进一步
			self.code_builder.backward()

	def _handle_include(self,tag,tag_name):
		filename=tag.split()[1].strip('"\'')
		included_template=self._parse_another_template_file(filename)
		#做成colsure
		self.code_builder.add(included_template.code_builder)
		#调用colsure函数返回结果 
		self.code_builder.add_line('{0}.append({1}())'.format(
													self.result_var,
													included_template.func_name))

	
	def _parse_another_template_file(self,filename):
		
		template_path = os.path.realpath(
							os.path.join(self.template_dir,filename)
							)
		name_suffix=str(hash(template_path)).replace('-','_')
		func_name='{}_{}'.format(self.func_name,name_suffix)
		result_var = '{}_{}'.format(self.result_var, name_suffix)
		with open(template_path) as fp:
			#此处相当于template=Template(......)
			template = self.__class__(
				fp.read(),indent=self.code_builder.indent,
				default_context=self.default_context,
				func_name=func_name,result_var=result_var,
				template_dir=self.template_dir)

		return template

	def _handle_extends(self):
		#得到 {% extends parent2.html %}
		match_extends = self.re_extends.match(self.raw_text)
		if match_extends is None:
			return
		#得到 parent2.html
		parent_template_name=match_extends.group('name').strip('"\' ')
		#得到 templates/parent2.html
		parent_template_path=os.path.join(self.template_dir,parent_template_name)

		#获取child2.html中的block
		child_blocks=self._get_all_blocks(self.raw_text)
		#{block_name:block_code}
		print "child_blocks: ",child_blocks
		with open(parent_template_path) as fp:
			parent_text = fp.read()

		#这里只是根据 parent2.html中有的block去替换，
		#child2.html中独特的内容会在后续的过程中被忽略
		new_parent_text = self._replace_parent_blocks(parent_text,child_blocks)
		
		#print "new_parent_text:",new_parent_text
		#设置得到结果的继承raw_text
		self.raw_text=new_parent_text

	def _replace_parent_blocks(self,parent_text,child_blocks):
		def replace(match):
			print "match: ",type(match),match.group(0)
			name=match.group('name')
			parent_code=match.group('code')
			print "parent_code: ",parent_code
			child_code = child_blocks.get(name, '')
			print "child_code: ",child_code
			#替换掉 block.super
			child_code = self.re_block_super.sub(parent_code, child_code)
			new_code = child_code or parent_code
			return new_code
			#replace 中的match 为 parent_text match re_blocks的文本

		print "parent_text: \n",parent_text
		replaced_text=self.re_blocks.sub('abc',parent_text)
		print "replaced text: \n",replaced_text
		return self.re_blocks.sub(replace,parent_text)

	def _get_all_blocks(self,text):
		'''
			得到 {% block header%}
					code
				 {% endblock header%}
		'''
		blocks=self.re_blocks.findall(text)
		#print "blocks: ",blocks
		return {name:code for name,code in blocks}


	def _parse_text(self):

		print 'raw_text: ',self.raw_text
		self._handle_extends()
		print 'raw_text: ',self.raw_text
		#任何有变量的地方都切割开
		tokens=self.re_tokens.split(self.raw_text)

		print 'tokens: ', tokens

		#print "tokens:",tokens
		handlers=self.handlers;
		for token in tokens:
			if token==None:
				continue
			for match,handler in handlers:
				if match(token):
					#print token,handler
					handler(token)
					break
			else:
				self.default_handler(token)


	def flush_buffer(self):
		line='{0}.extend([{1}])'.format(self.result_var,
									','.join(self.buffered))

		self.code_builder.add_line(line)
		self.buffered=[]

	def render(self,context=None):
		namespace={}
		namespace.update(self.default_context)
		if context:
			namespace.update(context)

		#创建 __func_name函数对象
		exec(str(self.code_builder),namespace)
		#print namespace[self.func_name].func_globals
		#print namespace[self.func_name]
		result=namespace[self.func_name]()
		return result

