import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import datetime
import os

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobradar_db')
DB_USER = os.getenv('DB_USER', 'jobradar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'jobradar123')

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

st.set_page_config(page_title="Job Radar", layout="wide")

st.sidebar.title("📡 Job Radar")
st.sidebar.markdown("---")
st.sidebar.markdown("### Sources")
st.sidebar.markdown("• Greenhouse")
st.sidebar.markdown("• Lever")
st.sidebar.markdown("• Workday")
st.sidebar.markdown("---")
st.sidebar.markdown("### Skills")
st.sidebar.markdown("**Dynamically Extracted via spaCy NLP**")
st.sidebar.markdown("No hardcoded skill lists.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"*Updated: {datetime.now().strftime('%H:%M')}*")

view = st.sidebar.radio("View", ["📊 Overview", "📈 Skills", "💼 Jobs", "📉 Trends", "🏢 Companies"])

conn = get_db_connection()
cur = conn.cursor()

if view == "📊 Overview":
    st.header("📊 Overview")
    
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM jobs WHERE posted_date = CURRENT_DATE")
    new_today = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT company) FROM jobs")
    total_companies = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT source) FROM jobs")
    total_sources = cur.fetchone()[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Jobs", total_jobs)
    col2.metric("New Today", new_today)
    col3.metric("Companies", total_companies)
    col4.metric("Sources", total_sources)
    
    # Source distribution
    st.subheader("📊 Jobs by Source")
    cur.execute("""
        SELECT source, COUNT(*) as count
        FROM jobs
        GROUP BY source
        ORDER BY count DESC
    """)
    source_data = cur.fetchall()
    if source_data:
        df = pd.DataFrame(source_data, columns=["Source", "Count"])
        fig = px.pie(df, values="Count", names="Source", title="Jobs by ATS")
        st.plotly_chart(fig, use_container_width=True)
    
    # Top skills today
    st.subheader("🏆 Top Skills Today (Dynamically Extracted)")
    cur.execute("""
        SELECT skill, count FROM skills_daily
        WHERE date = CURRENT_DATE
        ORDER BY rank LIMIT 10
    """)
    skills = cur.fetchall()
    if skills:
        df = pd.DataFrame(skills, columns=["Skill", "Count"])
        fig = px.bar(df, x="Count", y="Skill", orientation='h',
                     title="Top 10 Skills Today",
                     color_discrete_sequence=['#FF6B6B'])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No skills data yet. Run the collector first.")
    
    # Recent jobs
    st.subheader("🆕 Latest Jobs")
    cur.execute("""
        SELECT company, title, location, source, posted_date, url
        FROM jobs
        ORDER BY posted_date DESC, first_seen DESC
        LIMIT 10
    """)
    recent = cur.fetchall()
    if recent:
        df = pd.DataFrame(recent, columns=["Company", "Role", "Location", "Source", "Posted", "Apply"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No jobs collected yet")

elif view == "📈 Skills":
    st.header("📈 Skill Rankings (Dynamically Extracted from Job Descriptions)")
    
    period = st.selectbox("Period", ["Today", "This Week", "This Month"])
    
    if period == "Today":
        cur.execute("""
            SELECT skill, count FROM skills_daily
            WHERE date = CURRENT_DATE
            ORDER BY rank LIMIT 20
        """)
    elif period == "This Week":
        cur.execute("""
            SELECT skill, SUM(count) as total
            FROM skills_daily
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY skill
            ORDER BY total DESC LIMIT 20
        """)
    else:
        cur.execute("""
            SELECT skill, SUM(count) as total
            FROM skills_daily
            WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY skill
            ORDER BY total DESC LIMIT 20
        """)
    
    skills = cur.fetchall()
    
    if skills:
        df = pd.DataFrame(skills, columns=["Skill", "Count"])
        fig = px.bar(df, x="Count", y="Skill", orientation='h',
                     title=f"Top Skills ({period})",
                     color_discrete_sequence=['#4ECDC4'])
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Full List")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No skills data available yet")

elif view == "💼 Jobs":
    st.header("💼 Job Listings")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        company_filter = st.text_input("Company", "")
    with col2:
        location_filter = st.text_input("Location", "")
    with col3:
        source_filter = st.selectbox("Source", ["All", "greenhouse", "lever", "workday"])
    with col4:
        days_filter = st.number_input("Last N days", min_value=1, max_value=30, value=7)
    
    query = """
        SELECT company, title, location, source, posted_date, url
        FROM jobs
        WHERE posted_date >= CURRENT_DATE - INTERVAL %s DAY
    """
    params = [days_filter]
    
    if company_filter:
        query += " AND company ILIKE %s"
        params.append(f"%{company_filter}%")
    if location_filter:
        query += " AND location ILIKE %s"
        params.append(f"%{location_filter}%")
    if source_filter != "All":
        query += " AND source = %s"
        params.append(source_filter)
    
    query += " ORDER BY posted_date DESC, first_seen DESC LIMIT 100"
    
    cur.execute(query, params)
    jobs = cur.fetchall()
    
    if jobs:
        df = pd.DataFrame(jobs, columns=["Company", "Role", "Location", "Source", "Posted", "Apply"])
        st.dataframe(df, use_container_width=True, height=500)
        
        st.subheader("📊 Job Stats")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Jobs", len(jobs))
        col2.metric("Companies", df['Company'].nunique())
        col3.metric("Sources", df['Source'].nunique())
    else:
        st.info("No jobs match your filters")

elif view == "📉 Trends":
    st.header("📉 Skill Trends")
    
    cur.execute("""
        SELECT date, skill, count
        FROM skills_daily
        WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY date, rank
    """)
    
    trends = cur.fetchall()
    
    if trends:
        df = pd.DataFrame(trends, columns=["Date", "Skill", "Count"])
        top_skills = df.groupby('Skill')['Count'].sum().nlargest(5).index.tolist()
        df_filtered = df[df['Skill'].isin(top_skills)]
        
        fig = px.line(df_filtered, x="Date", y="Count", color="Skill",
                      title="Top 5 Skills Trend (Last 7 Days)",
                      markers=True)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📈 Growth This Week")
        for skill in top_skills:
            skill_data = df[df['Skill'] == skill]
            if len(skill_data) >= 2:
                first = skill_data.iloc[0]['Count']
                last = skill_data.iloc[-1]['Count']
                growth = ((last - first) / first * 100) if first > 0 else 0
                emoji = "📈" if growth > 0 else "📉" if growth < 0 else "➡️"
                st.write(f"{emoji} **{skill.title()}**: {growth:.1f}% ({first} → {last})")
        
        with st.expander("📋 Full Trend Data"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("Not enough data for trends yet (need at least 2 days of data)")

elif view == "🏢 Companies":
    st.header("🏢 Company Stats")
    
    cur.execute("""
        SELECT company, COUNT(*) as jobs, MAX(posted_date) as last_seen
        FROM jobs
        GROUP BY company
        ORDER BY jobs DESC
        LIMIT 50
    """)
    
    companies = cur.fetchall()
    
    if companies:
        df = pd.DataFrame(companies, columns=["Company", "Jobs", "Last Seen"])
        
        fig = px.bar(df.head(15), x="Jobs", y="Company", orientation='h',
                     title="Top 15 Companies by Job Count",
                     color_discrete_sequence=['#FFD93D'])
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No company data available")

conn.close()