import streamlit as st
from fastembed import TextEmbedding, SparseTextEmbedding, LateInteractionTextEmbedding
import logging

logger = logging.getLogger(__name__)

@st.cache_resource(show_spinner="Loading Embedding Models...")
def get_embedding_models():
    """
    Initializes and caches the FastEmbed models.
    Returns a tuple: (dense_model, sparse_model, colbert_model)
    """
    logger.info("Initializing Embedding Models (Dense, Sparse, ColBERT)...")

    # Dense (Multilingual, Lightweight)
    dense_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    dense_model = TextEmbedding(model_name=dense_model_name)

    # Sparse (BM25)
    # Note: FastEmbed sparse models are limited. Splade is English-optimized but we keep it for hybrid structure.
    sparse_model_name = "prithivida/Splade_PP_en_v1"
    sparse_model = SparseTextEmbedding(model_name=sparse_model_name)

    # ColBERT (Late Interaction, Multilingual, Small)
    colbert_model_name = "answerdotai/answerai-colbert-small-v1"
    colbert_model = LateInteractionTextEmbedding(model_name=colbert_model_name)

    logger.info("Embedding Models initialized successfully.")
    return dense_model, sparse_model, colbert_model
