from Andd_Baayi.settings import _normalise_database_url


def test_normalise_database_url_keeps_render_postgres_port():
    url = "postgresql://andd_baay:secret@dpg-example-a.frankfurt-postgres.render.com:5432/andd_baay"

    assert _normalise_database_url(url) == url


def test_normalise_database_url_moves_supabase_session_port_to_pooler():
    url = "postgresql://postgres:secret@db.project-ref.supabase.co:5432/postgres?pgbouncer=true&supa=base"

    assert (
        _normalise_database_url(url)
        == "postgresql://postgres:secret@db.project-ref.supabase.co:6543/postgres"
    )


def test_normalise_database_url_keeps_existing_supabase_pooler_port():
    url = "postgresql://postgres:secret@aws-0-eu.pooler.supabase.com:6543/postgres?sslmode=require"

    assert _normalise_database_url(url) == url
