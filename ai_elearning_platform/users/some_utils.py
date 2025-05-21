# In some_utils.py
from django.core.cache import cache

def get_cached_tfidf_data():
    tfidf_data = cache.get('global_tfidf_data')
    if not tfidf_data:
        # Compute vectorizer, matrix, course_ids_map
        # ...
        tfidf_data = {'vectorizer': ..., 'matrix': ..., 'ids_map': ...}
        cache.set('global_tfidf_data', tfidf_data, timeout=3600) # Cache for 1 hour
    return tfidf_data['vectorizer'], tfidf_data['matrix'], tfidf_data['ids_map']