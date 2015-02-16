"""
See http://johnmacfarlane.net/pandoc/README.html
for syntax.
"""
# Remaining key issue: github_md dialect hardcodes all the newlines so
# lines in paragraphs should be joined if the resulting Markdown text
# is published as an issue on github.com. (Difficult to solve. Current
# solution seems to be manual editing, which is doable for small
# documents and issues.)

import re, sys
from common import default_movie, plain_exercise, table_analysis, \
     insert_code_and_tex, bibliography, indent_lines
from html import html_movie, html_table
from misc import option

# Mapping of envirs to correct Pandoc verbatim environment
language2pandoc = dict(
    cod='Python', pro='Python',
    pycod='Python', pypro='Python',
    cycod='Python', cypro='Python',
    ccod='C', cpro='C',
    cppcod='Cpp', cpppro='Cpp',
    fcod='Fortran', fpro='Fortran',
    rbcod='Ruby', rbpro='Ruby',
    plcod='Perl', plpro='Perl',
    shcod='Shell', shpro='Shell',
    jscod='JavaScript', jspro='JavaScript',
    htmlcod='HTML', htmlpro='HTML', html='HTML',
    # sys, dat, csv, txt: no support for pure text,
    # just use a plain text block
    #sys='Bash',
    pyoptpro='Python', pyscpro='Python',
    ipy='Python', pyshell='Python')
    # (the "Python" typesetting is neutral if the text
    # does not parse as python)

def pandoc_title(m):
    title = m.group('subst')
    if option('strapdown'):
        # title is in <title> tag in INTRO for the header of the HTML output
        return ''
    elif option('strict_markdown_output'):
        return '# ' + title
    elif option('multimarkdown_output'):
        return 'Title: ' + title
    else:
        # pandoc-extended markdown syntax
        return '% ' + title

def pandoc_author(authors_and_institutions, auth2index,
                 inst2index, index2inst, auth2email):
    # List authors on multiple lines
    authors = []
    for author, i, e in authors_and_institutions:
        author = '**%s**' % author  # set in boldface
        if i is None:
            authors.append(author)
        else:
            authors.append(author + ' at ' + ' and '.join(i))

    plain_text = '### Author'
    if len(authors) > 1:
        plain_text += 's'
    plain_text += '\n\n' + '\n\n'.join(authors) + '\n\n'

    if option('strapdown'):
        return plain_text
    elif option('strict_markdown_output'):
        return plain_text
    elif option('multimarkdown_output'):
        return 'Author: ' + ', '.join(authors) + '\n'
    else:
        # pandoc-extended markdown syntax
        return '% ' + ';  '.join(authors) + '\n'


def pandoc_date(m):
    date = m.group('subst')
    if option('strapdown'):
        return '#### Date: ' + date
    elif option('strict_markdown_output'):
        return '#### Date: ' + date
    elif option('multimarkdown_output'):
        return 'Date: ' + date + '\n'
    else:
        # pandoc-extended markdown syntax
        return '% ' + date + '\n'

def pandoc_code(filestr, code_blocks, code_block_types,
                tex_blocks, format):
    """
    # We expand all newcommands now
    from html import embed_newcommands
    newcommands = embed_newcommands(filestr)
    if newcommands:
        filestr = newcommands + filestr
    """

    # Note: the tex code require the MathJax fix of doconce md2html
    # to insert right MathJax extensions to interpret align and labels
    # correctly.
    # (Also, doconce.py runs align2equations so there are no align/align*
    # environments in tex blocks.)
    for i in range(len(tex_blocks)):
        # Remove latex envir in single equations
        tex_blocks[i] = tex_blocks[i].replace(r'\[', '')
        tex_blocks[i] = tex_blocks[i].replace(r'\]', '')
        tex_blocks[i] = tex_blocks[i].replace(r'\begin{equation*}', '')
        tex_blocks[i] = tex_blocks[i].replace(r'\end{equation*}', '')
        #tex_blocks[i] = tex_blocks[i].replace(r'\[', '$$')
        #tex_blocks[i] = tex_blocks[i].replace(r'\]', '$$')
        # Check for illegal environments
        m = re.search(r'\\begin\{(.+?)\}', tex_blocks[i])
        if m:
            envir = m.group(1)
            if envir not in ('equation', 'equation*', 'align*', 'align',
                             'array'):
                print """\
*** warning: latex envir \\begin{%s} does not work well.
""" % envir
        # Add $$ on each side of the equation
        tex_blocks[i] = '$$\n' + tex_blocks[i] + '$$\n'
    # Note: HTML output from pandoc requires $$ while latex cannot have
    # them if begin-end inside ($$\begin{...} \end{...}$$)

    if option('strict_markdown_output'):
        # Code blocks are just indented
        for i in range(len(code_blocks)):
            code_blocks[i] = indent_lines(code_blocks[i], format)

    filestr = insert_code_and_tex(filestr, code_blocks, tex_blocks, format)

    github_md = option('github_md')

    if not option('strict_markdown_output'):
        pass
        if github_md:
            for key in language2pandoc:
                language2pandoc[key] = language2pandoc[key].lower()

        # Code blocks apply the ~~~~~ delimiter, with blank lines before
        # and after
        for key in language2pandoc:
            language = language2pandoc[key]
            if github_md:
                replacement = '\n```%s\n' % language2pandoc[key]
            else:
                # pandoc-extended Markdown
                replacement = '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~{.%s}\n' % language2pandoc[key]
                #replacement = '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~{.%s ,numberLines}\n' % language2pandoc[key]  # enable line numbering
            filestr = re.sub(r'^!bc\s+%s\s*\n' % key,
                             replacement, filestr, flags=re.MULTILINE)

        # any !bc with/without argument becomes an unspecified block
        if github_md:
            replacement = '\n```'
        else:
            replacement = '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
        filestr = re.sub(r'^!bc.*$', replacement, filestr, flags=re.MULTILINE)

        if github_md:
            replacement = '```\n'
        else:
            replacement = '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
        filestr = re.sub(r'^!ec\s*$', replacement, filestr, flags=re.MULTILINE)
    else:
        # Strict Markdown: just indented blocks
        filestr = re.sub(r'^!bc.*$', '', filestr, flags=re.MULTILINE)
        filestr = re.sub(r'^!ec\s*$', '', filestr, flags=re.MULTILINE)

    filestr = re.sub(r'^!bt *\n', '', filestr, flags=re.MULTILINE)
    filestr = re.sub(r'^!et *\n', '', filestr, flags=re.MULTILINE)

    # \eqref and labels will not work, but labels do no harm
    filestr = filestr.replace(' label{', ' \\label{')
    pattern = r'^label\{'
    filestr = re.sub(pattern, '\\label{', filestr, flags=re.MULTILINE)
    filestr = re.sub(r'\(ref\{(.+?)\}\)', r'\eqref{\g<1>}', filestr)

    # Final fixes

    # Seems that title and author must appear on the very first lines
    filestr = filestr.lstrip()

    # Enable tasks lists:
    #   - [x] task 1 done
    #   - [ ] task 2 not yet done
    if github_md:
        pattern = '^(\s+)\*\s+(\[[x ]\])\s+'
        filestr = re.sub(pattern, '\g<1>- \g<2> ', filestr, flags=re.MULTILINE)

    return filestr

def pandoc_table(table):
    if option('github_md'):
        text = html_table(table)
        # Fix the problem that `verbatim` inside the table is not
        # typeset as verbatim (according to the pandoc translator rules)
        # in the GitHub Issue Tracker
        text = re.sub(r'`([^`]+?)`', '<code>\g<1></code>', text)
        return text

    # else: Pandoc-extended Markdown syntax

        """

    Simple markdown tables look like this::

        Left         Right   Center     Default
        -------     ------ ----------   -------
        12              12     12            12
        123            123     123          123
        1                1      1             1

    """
    # Slight modification of rst_table

    column_width = table_analysis(table['rows'])
    ncolumns = len(column_width)
    column_spec = table.get('columns_align', 'c'*ncolumns).replace('|', '')
    heading_spec = table.get('headings_align', 'c'*ncolumns).replace('|', '')
    a2py = {'r': 'rjust', 'l': 'ljust', 'c': 'center'}
    s = ''  # '\n'
    for i, row in enumerate(table['rows']):
        #s += '    '  # indentation of tables
        if row == ['horizontal rule'] and i > 0 and i < len(table['rows'])-1:
            # No horizontal rule at the top and bottom, just after heading
            for w in column_width:
                s += '-'*w + '  '
        else:
            # check if this is a headline between two horizontal rules:
            if i == 1 and \
               table['rows'][i-1] == ['horizontal rule'] and \
               table['rows'][i+1] == ['horizontal rule']:
                headline = True
            else:
                headline = False

            for w, c, ha, ca in \
                    zip(column_width, row, heading_spec, column_spec):
                if headline:
                    s += getattr(c, a2py[ha])(w) + '  '
                elif row != ['horizontal rule']:
                    s += getattr(c, a2py[ca])(w) + '  '
        s += '\n'
    s += '\n'
    return s

def pandoc_figure(m):
    filename = m.group('filename')
    caption = m.group('caption').strip()
    opts = m.group('options').strip()

    if opts:
        info = [s.split('=') for s in opts.split()]
        opts = ' '.join(['%s=%s' % (opt, value)
                         for opt, value in info if opt not in ['frac']])

    # Save raw html with width etc in a comment so we have that info
    if caption:
        caption = '<p><em>%s</em></p>' % caption
    text = '<!-- <img src="%s" %s>%s -->\n' % (filename, opts, caption)
    text += '![%s](%s)' % (caption, filename)
    # regex for turning the figure spec into raw html:
    # re.sub(r'^<!-- (<img.+?>.*) -->\n!\[.+$', r'\g<1>', text, flags=re.MULTILINE)
    #print 'pandoc_figure:', text
    return text

def pandoc_ref_and_label(section_label2title, format, filestr):
    # .... see section ref{my:sec} is replaced by
    # see the section "...section heading..."
    pattern = r'[Ss]ection(s?)\s+ref\{'
    replacement = r'the section\g<1> ref{'
    filestr = re.sub(pattern, replacement, filestr)
    pattern = r'[Cc]hapter(s?)\s+ref\{'
    replacement = r'the chapter\g<1> ref{'
    filestr = re.sub(pattern, replacement, filestr)

    # Need special adjustment to handle start of sentence (capital) or not.
    pattern = r'([.?!]\s+|\n\n|^#+ .+?\n+)the (sections?|chapters?)\s+ref'
    replacement = r'\g<1>The \g<2> ref'
    filestr = re.sub(pattern, replacement, filestr, flags=re.MULTILINE)

    # Remove Exercise, Project, Problem in references since those words
    # are used in the title of the section too
    pattern = r'(the\s*)?([Ee]xercises?|[Pp]rojects?|[Pp]roblems?)\s+ref\{'
    replacement = r' ref{'
    filestr = re.sub(pattern, replacement, filestr)

    # Replace all references to sections. Pandoc needs a coding of
    # the section header as link. (Not using this anymore.)
    def title2pandoc(title):
        # http://johnmacfarlane.net/pandoc/README.html
        for c in ('?', ';', ':'):
            title = title.replace(c, '')
        title = title.replace(' ', '-').strip()
        start = 0
        for i in range(len(title)):
            if title[i].isalpha():
                start = i
        title = title[start:]
        title = title.lower()
        if not title:
            title = 'section'
        return title

    for label in section_label2title:
        filestr = filestr.replace('ref{%s}' % label,
                  '[%s](#%s)' % (section_label2title[label],
                                 label))
     #                            title2pandoc(section_label2title[label])))

    # Treat the remaining ref{}
    # Note done.
    # Can place labels in equations as <a name tags before the equation
    # environment and create appropriate [link](#label) syntax.
    # Need to specify figures and movies separately to find the
    # right link text. html.py has probably most solutions.
    filestr = re.sub(r'([Ff]igure|[Mm]ovie)\s+ref\{(.+?)\}', '[\g<1>](#\g<2>)',
                     filestr)
    return filestr


def pandoc_index_bib(filestr, index, citations, pubfile, pubdata):
    # pandoc citations are of the form
    # bla-bla, see [@Smith04, ch. 1; @Langtangen_2008]
    # Method: cite{..} -> [...], doconce.py has already fixed @ and ;
    filestr = re.sub(r'cite\{(.+?)\}', r'[\g<1>]', filestr)

    if pubfile is not None:
        bibtext = bibliography(pubdata, citations, format='doconce')
        filestr = re.sub(r'^BIBFILE:.+$', bibtext, filestr, flags=re.MULTILINE)

    # pandoc does not support index entries,
    # remove all index entries (could also place them
    # in special comments to keep the information)

    filestr = re.sub(r'idx\{.+?\}' + '\n?', '', filestr)

    # Use HTML anchors for labels and [link text](#label) for references
    # outside mathematics.
    #filestr = re.sub(r'label\{(.+?)\}', '<a name="\g<1>"></a>', filestr)
    # Note: HTML5 should have <sometag id="..."></sometag> instead
    filestr = re.sub(r'label\{(.+?)\}', '<div id="\g<1>"></div>', filestr)

    return filestr

def pandoc_quote(block, format, text_size='normal'):
    # block quotes in pandoc start with "> "
    lines = []
    for line in block.splitlines():
        lines.append('> ' + line)
    return '\n'.join(lines) + '\n\n'

def pandoc_quiz(quiz):
    return '*Cannot typeset quiz*: "%s"' % quiz.get('question', '')

def define(FILENAME_EXTENSION,
           BLANKLINE,
           INLINE_TAGS_SUBST,
           CODE,
           LIST,
           ARGLIST,
           TABLE,
           EXERCISE,
           FIGURE_EXT,
           CROSS_REFS,
           INDEX_BIB,
           TOC,
           ENVIRS,
           QUIZ,
           INTRO,
           OUTRO,
           filestr):
    # all arguments are dicts and accept in-place modifications (extensions)

    FILENAME_EXTENSION['pandoc'] = '.md'
    BLANKLINE['pandoc'] = '\n'
    # replacement patterns for substitutions of inline tags
    INLINE_TAGS_SUBST['pandoc'] = {
        'math':      None,  # indicates no substitution, leave as is
        'math2':     r'\g<begin>$\g<latexmath>$\g<end>',
        'emphasize': None,
        'bold':      r'\g<begin>**\g<subst>**\g<end>',
        'figure':    pandoc_figure,
        #'movie':     default_movie,
        'movie':     html_movie,
        'verbatim':  None,
        #'linkURL':   r'\g<begin>\g<link> (\g<url>)\g<end>',
        'linkURL2':  r'[\g<link>](\g<url>)',
        'linkURL3':  r'[\g<link>](\g<url>)',
        'linkURL2v': r'[`\g<link>`](\g<url>)',
        'linkURL3v': r'[`\g<link>`](\g<url>)',
        'plainURL':  r'<\g<url>>',
        'colortext':     r'<font color="\g<color>">\g<text></font>',  # HTML
        # "Reference links" in pandoc are not yet supported
        'title':     pandoc_title,
        'author':    pandoc_author,
        'date':      pandoc_date,
        'chapter':       lambda m: '# '    + m.group('subst'),
        'section':       lambda m: '## '   + m.group('subst'),
        'subsection':    lambda m: '### '  + m.group('subst'),
        'subsubsection': lambda m: '#### ' + m.group('subst') + '\n',
        'paragraph':     r'*\g<subst>*\g<space>',
        'abstract':      r'*\g<type>.* \g<text>\n\n\g<rest>',
        'comment':       '<!-- %s -->',
        'linebreak':     r'\g<text>\\n',
        'non-breaking-space': '\\ ',
        'ampersand2':    r' \g<1>&\g<2>',
        }

    CODE['pandoc'] = pandoc_code
    ENVIRS['pandoc'] = {
        'quote':        pandoc_quote,
        }

    from common import DEFAULT_ARGLIST
    ARGLIST['pandoc'] = DEFAULT_ARGLIST
    LIST['pandoc'] = {
        'itemize':
        {'begin': '', 'item': '*', 'end': '\n'},

        'enumerate':
        {'begin': '', 'item': '%d.', 'end': '\n'},

        'description':
        {'begin': '', 'item': '%s\n  :   ', 'end': '\n'},

        #'separator': '\n',
        'separator': '',
        }
    CROSS_REFS['pandoc'] = pandoc_ref_and_label

    TABLE['pandoc'] = pandoc_table
    INDEX_BIB['pandoc'] = pandoc_index_bib
    EXERCISE['pandoc'] = plain_exercise
    TOC['pandoc'] = lambda s: '# Table of contents: Run pandoc with --toc option'
    QUIZ['pandoc'] = pandoc_quiz
    FIGURE_EXT['pandoc'] = ('.png', '.gif', '.jpg', '.jpeg', '.tif', '.tiff', '.pdf')

    # Wrap markdown output in strapdown HTML code for quick auto rendering
    # with Bootstrap themes?
    if option('strapdown'):
        # Themes
        boostrap_bootwatch_theme = option('bootswatch_theme=', 'spacelab')
        # Grab title
        title = ''
        if 'TITLE:' in filestr:
            for line in filestr.splitlines():
                if line.startswith('TITLE:'):
                    title = line.split('TITLE:')[-1].strip()
                    break
        INTRO['pandoc'] = """<!DOCTYPE html>
<html>
<title>%(title)s</title>

<xmp theme="%(boostrap_bootwatch_theme)s" style="display:none;">
# Markdown text goes in here
""" % vars()
        OUTRO['pandoc'] = """
</xmp>

<script src="http://strapdownjs.com/v/0.2/strapdown.js"></script>
</html>
"""
