import streamlit as st

def set_background_color(color):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {color};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def apply_common_styles():
    st.markdown("""
    <style>
    .stButton button {
        background-color: #3897f0;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stTextInput input {
        border-radius: 5px;
        border: 1px solid #ddd;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Fonction pour injecter le JavaScript de navigation
def add_enter_navigation():
    st.markdown(
        """
        <script>
        document.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                const inputs = document.querySelectorAll("input");
                const currentInput = document.activeElement;
                let nextInput = null;

                for (let i = 0; i < inputs.length; i++) {
                    if (inputs[i] === currentInput && i < inputs.length - 1) {
                        nextInput = inputs[i + 1];
                        break;
                    }
                }

                if (nextInput) {
                    nextInput.focus();
                    event.preventDefault();
                }
            }
        });
        </script>
        """,
        unsafe_allow_html=True,
    )
