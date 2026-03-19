from pygments.formatters import HtmlFormatter

formatter = HtmlFormatter(style='monokai')
# .highlight is the default class for Pygments
css = formatter.get_style_defs('.highlight')
print(f"CSS:\n{css[:200]}...")
