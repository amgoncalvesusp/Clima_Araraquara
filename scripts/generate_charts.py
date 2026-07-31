import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_CSV = os.path.join(BASE_DIR, "data", "ranking_risco_termico.csv")
CHARTS_DIR = os.path.join(BASE_DIR, "web", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

def generate_visualizations():
    print("Generating analytical charts for PET Clima Araraquara...")
    df = pd.read_csv(DATA_CSV)
    
    # Set aesthetics
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.sans-serif': 'Arial', 'font.family': 'sans-serif'})
    
    # 1. Scatter Plot: Surface Temp vs. NDVI (Vegetation) colored by IECS Risk Score
    plt.figure(figsize=(10, 6))
    scatter = sns.scatterplot(
        data=df,
        x="ndvi_300m",
        y="surface_temp_300m",
        hue="iecs_score",
        size="vulnerability_score_300m",
        sizes=(40, 200),
        palette="YlOrRd",
        alpha=0.85
    )
    
    # Add Trend Line
    sns.regplot(
        data=df,
        x="ndvi_300m",
        y="surface_temp_300m",
        scatter=False,
        ax=plt.gca(),
        color="crimson",
        line_kws={"linestyle": "--", "linewidth": 1.8}
    )
    
    plt.title("Correlação Espacial: Temperatura de Superfície vs. Vegetação (NDVI - 300m)", fontsize=14, pad=15, fontweight="bold")
    plt.xlabel("Índice de Cobertura Vegetal (NDVI no raio de 300m)", fontsize=12)
    plt.ylabel("Temperatura Média de Superfície (°C no raio de 300m)", fontsize=12)
    plt.colorbar(scatter.collections[0], label="Índice de Exposição Climática (IECS 0-100)")
    
    chart1_path = os.path.join(CHARTS_DIR, "correlacao_temp_ndvi.png")
    plt.savefig(chart1_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart 1 saved to {chart1_path}")
    
    # 2. Bar Chart: Top 10 Most Vulnerable Healthcare Units
    plt.figure(figsize=(12, 7))
    top10 = df.head(10).sort_values(by="iecs_score", ascending=True)
    
    colors = ["#e63946" if s >= 75 else "#f4a261" for s in top10["iecs_score"]]
    bars = plt.barh(top10["name"], top10["iecs_score"], color=colors, edgecolor="black", alpha=0.85)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1.2, bar.get_y() + bar.get_height()/2, f"{width:.1f}", 
                 va="center", ha="left", fontsize=10, fontweight="bold")
                 
    plt.title("Top 10 Unidades de Saúde de Araraquara mais Expostas ao Risco Térmico", fontsize=14, pad=15, fontweight="bold")
    plt.xlabel("Índice de Exposição Climática e Social (IECS 0-100)", fontsize=12)
    plt.ylabel("Unidade de Saúde", fontsize=12)
    plt.xlim(0, 105)
    
    chart2_path = os.path.join(CHARTS_DIR, "top10_unidades_criticas.png")
    plt.savefig(chart2_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart 2 saved to {chart2_path}")
    
    # 3. Risk Level Distribution Pie / Donut Chart
    plt.figure(figsize=(7, 7))
    risk_counts = df["risk_level"].value_counts()
    colors_dict = {
        "Crítico (Altíssimo Risco)": "#d90429",
        "Alto": "#f77f00",
        "Moderado": "#fcbf49",
        "Baixo / Confortável": "#2a9d8f"
    }
    palette = [colors_dict.get(k, "#8d99ae") for k in risk_counts.index]
    
    plt.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%',
            startangle=140, colors=palette, wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2))
            
    plt.title("Distribuição das Unidades de Saúde por Nível de Risco Climático", fontsize=14, pad=15, fontweight="bold")
    
    chart3_path = os.path.join(CHARTS_DIR, "distribuicao_niveis_risco.png")
    plt.savefig(chart3_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Chart 3 saved to {chart3_path}")

if __name__ == "__main__":
    generate_visualizations()
