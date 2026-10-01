"""
PromoBox — Dashboard principal.
"Suas melhores ofertas, no automático."
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Garante que a raiz do projeto esteja no sys.path, mesmo em ambientes de
# deploy (ex: Streamlit Cloud) que às vezes não adicionam o diretório do
# script automaticamente — evita "ModuleNotFoundError: No module named 'app'".
_PROJECT_ROOT = _Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from app.components.auth import require_login
from app.components.layout import bootstrap, page_header
from app.database.db import get_session
from app.database.models import (
    Click, Conversion, Offer, OfferStatus, Product, PublishedPost, ScheduledPost,
)
from app.utils.config import settings

st.set_page_config(page_title="PromoBox", page_icon="📦", layout="wide")

bootstrap()
require_login()
page_header("Dashboard", "📊")

st.caption("Suas melhores ofertas, no automático.")

session = get_session()
try:
    demo = settings.demo_mode

    total_offers = session.query(Offer).filter(Offer.is_demo == demo).count()
    scheduled = session.query(ScheduledPost).filter(
        ScheduledPost.is_demo == demo, ScheduledPost.status == "PROGRAMADA"
    ).count()
    published = session.query(ScheduledPost).filter(
        ScheduledPost.is_demo == demo, ScheduledPost.status == "PUBLICADA"
    ).count()
    with_error = session.query(ScheduledPost).filter(
        ScheduledPost.is_demo == demo, ScheduledPost.status == "ERRO"
    ).count()
    expired = session.query(Offer).filter(
        Offer.is_demo == demo, Offer.status == OfferStatus.EXPIRADA
    ).count()

    total_clicks = (
        session.query(Click).join(PublishedPost).join(ScheduledPost)
        .filter(ScheduledPost.is_demo == demo).count()
    )
    total_conversions = (
        session.query(Conversion).join(PublishedPost).join(ScheduledPost)
        .filter(ScheduledPost.is_demo == demo).count()
    )
    estimated_commission = sum(
        c.commission_value for c in
        session.query(Conversion).join(PublishedPost).join(ScheduledPost)
        .filter(ScheduledPost.is_demo == demo).all()
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ofertas cadastradas", total_offers)
    col2.metric("Programadas", scheduled)
    col3.metric("Publicadas", published)
    col4.metric("Com erro", with_error)

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Expiradas", expired)
    col6.metric("Total de cliques", total_clicks)
    col7.metric("Conversões", total_conversions if total_conversions else "—")
    col8.metric("Comissão estimada", f"R$ {estimated_commission:,.2f}" if total_conversions else "Sem dados")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("#### 🏆 Produtos mais clicados")
        rows = (
            session.query(Product.name, session.query(Click).join(PublishedPost).join(ScheduledPost)
                           .filter(ScheduledPost.offer.has(product_id=Product.id)).count())
            .filter(Product.is_demo == demo)
            .limit(5)
            .all()
        )
        clique_data = []
        for offer in session.query(Offer).filter(Offer.is_demo == demo).limit(20).all():
            n_clicks = (
                session.query(Click).join(PublishedPost).join(ScheduledPost)
                .filter(ScheduledPost.offer_id == offer.id).count()
            )
            if n_clicks > 0:
                clique_data.append({"Produto": offer.product.name, "Cliques": n_clicks})
        if clique_data:
            df = pd.DataFrame(clique_data).sort_values("Cliques", ascending=False).head(5)
            st.bar_chart(df.set_index("Produto"))
        else:
            st.info("Ainda não há cliques registrados." if not demo else
                     "Sem cliques ainda — gere publicações DEMO na página de Analytics para simular dados.")

    with right:
        st.markdown("#### 📂 Categorias com melhor desempenho")
        cat_data = []
        from app.database.models import Category
        for cat in session.query(Category).all():
            n_offers = (
                session.query(Offer).filter(Offer.is_demo == demo)
                .filter(Offer.product.has(category_id=cat.id)).count()
            )
            if n_offers > 0:
                cat_data.append({"Categoria": cat.name, "Ofertas": n_offers})
        if cat_data:
            df = pd.DataFrame(cat_data).sort_values("Ofertas", ascending=False)
            st.bar_chart(df.set_index("Categoria"))
        else:
            st.info("Nenhuma categoria com ofertas ainda.")

    st.divider()
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🕓 Últimas publicações")
        recent = (
            session.query(ScheduledPost)
            .filter(ScheduledPost.is_demo == demo, ScheduledPost.status == "PUBLICADA")
            .order_by(ScheduledPost.processed_at.desc())
            .limit(6)
            .all()
        )
        if recent:
            for p in recent:
                st.write(f"✅ **{p.offer.product.name}** — {p.channel.name} — "
                         f"{p.processed_at.strftime('%d/%m %H:%M') if p.processed_at else ''}")
        else:
            st.info("Nenhuma publicação realizada ainda. Rode o worker ou use o botão de simulação em Agendamento.")

    with col_b:
        st.markdown("#### 📅 Próximas publicações")
        upcoming = (
            session.query(ScheduledPost)
            .filter(ScheduledPost.is_demo == demo, ScheduledPost.status == "PROGRAMADA")
            .order_by(ScheduledPost.scheduled_date.asc())
            .limit(6)
            .all()
        )
        if upcoming:
            for p in upcoming:
                st.write(f"⏳ **{p.offer.product.name}** — {p.category_label} — "
                         f"{p.scheduled_date.strftime('%d/%m %H:%M')}")
        else:
            st.info("Nenhuma publicação programada. Vá em Agendamento e monte a fila do dia.")

finally:
    session.close()

st.divider()
st.caption(
    "👈 Use o menu lateral para cadastrar ofertas, importar dados, configurar canais, "
    "agendar publicações e acompanhar analytics."
)
