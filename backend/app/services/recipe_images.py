from sqlmodel import Session, select

from ..models import RecipeImage


def cover_url_for_recipe(session: Session, recipe_id: int) -> str | None:
    image = session.exec(
        select(RecipeImage).where(
            RecipeImage.recipe_id == recipe_id,
            RecipeImage.is_cover.is_(True),
        )
    ).first()
    if image is None:
        return None
    return f"/uploads/{image.file_path}"
