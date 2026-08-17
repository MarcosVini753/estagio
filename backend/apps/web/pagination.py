from django.core.paginator import Paginator

PAGE_SIZE = 25


def paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
