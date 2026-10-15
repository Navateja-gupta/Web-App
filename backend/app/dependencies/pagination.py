from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True)
class PageParams:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def get_page_params(
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
) -> PageParams:
    return PageParams(page=page, size=size)
