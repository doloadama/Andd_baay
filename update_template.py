import re
import os

filepath = os.path.join('templates', 'projets', 'detail_projet.html')
with open(filepath, 'r', encoding='utf-8') as f:
    c = f.read()

c = re.sub(
    r'(<i class="fas fa-seedling"></i> \{\{ pp\.produit\.nom \}\}\s+)(\{% if pp\.rendement_final %\})',
    r'\1{% if pp.age_plant %}<span class="ms-1" style="opacity: 0.8;">({{ pp.age_plant }} jrs)</span>{% endif %}\n                                                \2',
    c
)

c = re.sub(
    r'(<h5><i class="fas fa-camera text-accent me-2"></i> )Galerie de Culture(</h5>\s+</div>\s+<div class="glass-card-body p-3">).*?(</div>\s+</div>\s+</div>\s+<!-- Right Column -->)',
    r'''\1Suivi des plants (Photos)\2
                    {% if plant_photos %}
                        <div id="photoCarousel" class="carousel slide" data-bs-ride="carousel" style="border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                            <div class="carousel-inner">
                                {% for photo in plant_photos %}
                                    <div class="carousel-item {% if forloop.first %}active{% endif %}">
                                        <img src="{{ photo.url }}" alt="{{ photo.title }}" class="d-block w-100 object-fit-cover" style="height: 350px;" data-bs-toggle="tooltip" title="{{ photo.subtitle }}">
                                        <div class="carousel-caption d-none d-md-block" style="background: rgba(0,0,0,0.6); border-radius: 12px; padding: 10px; bottom: 20px;">
                                            <h6 class="mb-1 text-white">{{ photo.title }}</h6>
                                            {% if photo.subtitle %}<p class="mb-0 small text-white-50">{{ photo.subtitle }}</p>{% endif %}
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                            {% if plant_photos|length > 1 %}
                            <button class="carousel-control-prev" type="button" data-bs-target="#photoCarousel" data-bs-slide="prev">
                                <span class="carousel-control-prev-icon shadow-sm" style="background-color: rgba(0,0,0,0.5); border-radius: 50%; padding: 20px;"></span>
                            </button>
                            <button class="carousel-control-next" type="button" data-bs-target="#photoCarousel" data-bs-slide="next">
                                <span class="carousel-control-next-icon shadow-sm" style="background-color: rgba(0,0,0,0.5); border-radius: 50%; padding: 20px;"></span>
                            </button>
                            {% endif %}
                        </div>
                    {% else %}
                        <div class="text-center py-5 text-muted">
                            <i class="fas fa-image fs-1 mb-3 opacity-50"></i>
                            <p>Aucune photo n'a été ajoutée à ce projet.</p>
                        </div>
                    {% endif %}
\3''',
    c,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(c)

print("Template updated successfully!")
