from rest_framework.pagination import PageNumberPagination, CursorPagination


class StandardPagination(PageNumberPagination):
    """Standard offset-based pagination for most endpoints."""
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
    page_query_param = "page"


class CursorBasedPagination(CursorPagination):
    """Cursor-based pagination for high-volume feeds (events, notifications)."""
    page_size = 50
    ordering = "-created_at"
    cursor_query_param = "cursor"
