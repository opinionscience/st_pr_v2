import streamlit as st
from opsci_toolbox.helpers.common import load_pickle, read_json
from opsci_toolbox.helpers.nlp import sample_most_engaging_posts
from opsci_toolbox.helpers.dataviz import subplots_bar_per_day_per_cat, create_scatter_plot, add_shape, pie, network_graph
from opsci_toolbox.helpers.sna import *
from opsci_toolbox.helpers.nlp import load_stopwords_df
from eldar import Query
import plotly.express as px

def format_number(number):
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f"{number / 1000:.1f}K"
    elif number < 1000000000:
        return f"{number / 1000000:.1f}M"
    else:
        return f"{number / 1000000000:.1f}B"

def main():
    st.set_page_config(
        page_title="Search engine",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title('Settings')

    ###############################################
    # LOAD DATA
    ###############################################
    df = pd.read_pickle("data/df_prod_chroma_v2.pickle")
    df["datetime"]= pd.to_datetime(df["date"])

    plateforme_color_palette = read_json("data/plateforme_color_palette.json")

    ###############################################
    # SIDEBAR SETTINGS / PARAMETERS
    ###############################################
    txt_query_telegram = st.sidebar.text_area("Search on Telegram", value="macron", height=None, max_chars=None, key=None, help=None, on_change=None, args=None, kwargs=None, placeholder=None, disabled=False, label_visibility="visible")
    txt_query_twitter = st.sidebar.text_area("Search on Twitter", value="macron", height=None, max_chars=None, key=None, help=None, on_change=None, args=None, kwargs=None, placeholder=None, disabled=False, label_visibility="visible")
    
    date = st.sidebar.date_input("Timerange", value = [df['datetime'].min(), df['datetime'].max()], min_value=df['datetime'].min(), max_value=df['datetime'].max(), format="YYYY/MM/DD", label_visibility="visible")
    lang = st.sidebar.selectbox("Language", ['english', 'russian'], index = 0, placeholder="Choose an option", label_visibility="visible")
    ignore_case = st.sidebar.toggle("Ignore case", value=True, label_visibility="visible")
    ignore_accent = st.sidebar.toggle("Ignore accent", value=True, label_visibility="visible")
    match_word = st.sidebar.toggle("Match words", value=True, label_visibility="visible")
    rolling_period = st.sidebar.text_input("Rolling period", value='7D', label_visibility="visible")
   
    ###############################################
    # DATA FILTERING
    ###############################################
    if lang == "english":
        col_search = "translated_text"
    else :
        col_search = "text"

    df['datetime'] = df['datetime'].dt.date
    df = df[(df['datetime'] >= date[0]) & (df['datetime'] <= date[1])]


    df_twitter = df[df['plateforme']=="Twitter"].reset_index(drop=True)
    df_telegram = df[df['plateforme']=="Telegram"].reset_index(drop=True)

    boolean_query_telegram = Query(txt_query_telegram, ignore_case=ignore_case, ignore_accent=ignore_accent, match_word=match_word)
    df_telegram = df_telegram[df_telegram[col_search].apply(boolean_query_telegram)]

    boolean_query_twitter = Query(txt_query_twitter, ignore_case=ignore_case, ignore_accent=ignore_accent, match_word=match_word)
    df_twitter = df_twitter[df_twitter['text'].apply(boolean_query_twitter)]

    df_new = pd.concat([df_telegram, df_twitter]).reset_index()
    
    ###############################################
    # DATA FILTERING
    ###############################################
    total_posts_telegram = df[df['plateforme']=='Telegram']['message_id'].nunique()
    total_channels_telegram = df[df['plateforme']=='Telegram']['user_id'].nunique()
    sum_views_telegram = df[df['plateforme']=='Telegram']['views'].sum()
    sum_eng_telegram = df[df['plateforme']=='Telegram']['engagements'].sum()

    total_posts_twitter = df[df['plateforme']=='Twitter']['message_id'].nunique()
    total_channels_twitter = df[df['plateforme']=='Twitter']['user_id'].nunique()
    sum_views_twitter = df[df['plateforme']=='Twitter']['views'].sum()
    sum_eng_twitter = df[df['plateforme']=='Twitter']['engagements'].sum()

    ################################################
    # DATA PREP
    ################################################
    metrics = {
    'posts' : ('message_id',"nunique"),
    'views': ('views', 'sum'),
    'engagements': ('engagements', 'sum'),
    'share': ('share', 'sum'),
    'likes': ('likes', 'sum'),
    'comments': ('comments', 'sum')
    }

    df_trends_channels = df_new.copy()
    df_trends_channels["datetime"]= pd.to_datetime(df_trends_channels["date"])
    df_trends_channels.set_index('datetime', inplace=True)
    df_trends_channels = df_trends_channels.groupby("plateforme").resample(rolling_period).agg(**metrics).reset_index()
    df_trends_channels["datetime"]=df_trends_channels["datetime"].dt.strftime("%Y-%m-%d")
    df_trends_channels['color'] = df_trends_channels['plateforme'].map(plateforme_color_palette)

    ###############################################
    # KEY METRICS
    ###############################################

    fig = px.line(df_trends_channels, x='datetime', y='posts', color='plateforme')
    st.plotly_chart(fig, use_container_width=True, sharing="streamlit", theme="streamlit")

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.title("Telegram")
        sub_col1, sub_col2, sub_col3, sub_col4 = st.columns(4, gap="small")

        with sub_col1:
            st.metric("Verbatims", format_number(df_telegram['message_id'].nunique()), label_visibility="visible")
            st.write('{:.2%}'.format(df_telegram['message_id'].nunique()/total_posts_telegram))
        with sub_col2:
            st.metric("Channels", format_number(df_telegram['user_id'].nunique()), label_visibility="visible")
            st.write('{:.2%}'.format(df_telegram['user_id'].nunique()/total_channels_telegram))
        with sub_col3:
            st.metric("Views", format_number(df_telegram['views'].sum()), label_visibility="visible")
            st.write('{:.2%}'.format(df_telegram['views'].sum()/sum_views_telegram))
        with sub_col4:
            st.metric("Engagements", format_number(df_telegram['engagements'].sum()), label_visibility="visible")
            st.write('{:.2%}'.format(df_telegram['engagements'].sum()/sum_eng_telegram))
        for i, row in df_telegram.sort_values(by="engagements", ascending=False).iterrows():
            st.write('*'*50)
            st.write(f"<b>{row['user_name']} - {row['date']}</b>", unsafe_allow_html=True)
            st.write(row['translated_text'])
            st.write(f"<b>Engagements - {format_number(row['engagements'])} | Views - {format_number(row['views'])} | Shares - {format_number(row['share'])} | Likes - {format_number(row['likes'])} | Comments - {format_number(row['comments'])}</b>", unsafe_allow_html=True)

    with col2:
        st.title("Twitter")
        t_sub_col1, t_sub_col2, t_sub_col3, t_sub_col4 = st.columns(4, gap="small")

        with t_sub_col1:
            st.metric("Verbatims", format_number(df_twitter['message_id'].nunique()), label_visibility="visible")
            st.write('{:.2%}'.format(df_twitter['message_id'].nunique()/total_posts_twitter))
        with t_sub_col2:
            st.metric("Channels", format_number(df_twitter['user_id'].nunique()), label_visibility="visible")
            st.write('{:.2%}'.format(df_twitter['user_id'].nunique()/total_channels_twitter))
        with t_sub_col3:
            st.metric("Views", format_number(df_twitter['views'].sum()), label_visibility="visible")
            st.write('{:.2%}'.format(df_twitter['views'].sum()/sum_views_twitter))
        with t_sub_col4:
            st.metric("Engagements", format_number(df_twitter['engagements'].sum()), label_visibility="visible")
            st.write('{:.2%}'.format(df_twitter['engagements'].sum()/sum_eng_twitter))
        
        for i, row in df_twitter.sort_values(by="engagements", ascending=False).iterrows():
            st.write('*'*50)
            st.write(f"<b>{row['user_name']} - {row['date']}</b>", unsafe_allow_html=True)
            st.write(row['text'])
            st.write(f"<b>Engagements - {format_number(row['engagements'])} | Views - {format_number(row['views'])} | Shares - {format_number(row['share'])} | Likes - {format_number(row['likes'])} | Comments - {format_number(row['comments'])}</b>", unsafe_allow_html=True)
            st.write(f'<a href="https://www.twitter.com/{row["user_name"]}/status/{row["message_id"]}">Voir le tweet</a>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()