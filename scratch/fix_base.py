import os

with open('templates/base.html.tmp', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('href="{% static \'CSS/base.css\' %}"', 'href="{% static \'css/base.css\' %}"')

with open('templates/base.html', 'w', encoding='utf-8') as f:
    f.write(text)

os.remove('templates/base.html.tmp')
print("Successfully replaced base.html")
