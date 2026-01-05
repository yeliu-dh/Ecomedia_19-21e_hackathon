import pandas as pd
import re
import os, sys
import ast
from tqdm import tqdm
tqdm.pandas()
import time
import matplotlib.pyplot as plt
import seaborn as sns


def read_csv_with_list(csv_path, col_list):
    df=pd.read_csv(csv_path)

    df[col_list] = df[col_list].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    return df


def clean_ponc(s):
        '''
        eliminer - à gauche
        enliminer la ponctuation à droit 
        laisser tel quel le trait d'union au milieu
        si ',', prend ce qui est devant ','
       
        '''
        s = re.sub(r'^[-]+|[^\w]+$', '', s.strip())
        s=s.split(",")[0]        
        return s.strip()


def extract_loc(loc):
    loc=str(loc).strip().lower()
    #if exists (),prend ()
    if "(" in loc:          
        #trouver ce qui est entre ():
        bwt_parentheis = re.findall(r"\((.*?)\)", loc)[0] # within first ()
        
        # si c'est pas une pos, prend ce qui est entre () 
        parts=re.split(r"[- ]",bwt_parentheis)#séparer par trait d'union ou espace
        pos=["nord",'est','ouest',"sud","centre"]
        contains_pos=bool(set(pos)&set(parts))

        if contains_pos == False:
            clean_loc=bwt_parentheis

        # if bwt_parentheis not in ["nord",'sud',"ouest",'est','centre','sud-ouest',"nord-est"]:
        #     clean_loc=bwt_parentheis
            # print(f"① ():{bwt_parentheis}")
                
        # sinon, reviens au loc, eliminer la ponctuation et prend la 1e partie
        else :
            clean_loc=re.sub(r"\(.*?\)",'',loc).strip()#1e part,  elimine ce qui est() .*? → n'import quel contenu 
            clean_loc=clean_ponc(clean_loc)
            # print(f"② 1e part :{clean_loc}")
           
    # no (): take the 1e de loc
    else :
        clean_loc=clean_ponc(loc)
        # print(f'③ no():{clean_loc}')
    
    if "france" in clean_loc:
        clean_loc='france'
    return clean_loc

def roman_to_int(s):
    roman_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s = s.upper()
    total = 0
    prev_value = 0
    for char in reversed(s):
        value = roman_dict.get(char, 0)
        if value < prev_value:
            total -= value
        else:
            total += value
            prev_value = value
    return str(total)

def extract_year(s):
    list_years=[]
    # s'il y a '=', prend le texte après '='
    if '=' in s:
        s=s.split('=')[-1]
    list_years=re.findall(r'\b\d{4}\b', s)
    return list_years

def year_s_to_centry_s(year):
    return str(int(year)//100+1)    

def extract_date(date):
    date=str(date).strip()

    #chercher les lettres romanes:
    roman_dates = re.findall(r'\b([IVXLCDM]+)(?:e|er)?\b', date) #que majuscule
    # print('roman:',roman_dates)

    if roman_dates:
        arabic_dates=list(set([roman_to_int(match) for match in roman_dates]))
        # print(f"{date} =>{roman_dates} => {arabic_dates}")
        return arabic_dates
    
    #chercher les années sous forme de XXXX:
    years=extract_year(date)
    # print('yrs:',years)
    if years:
        centuries=list(set([year_s_to_centry_s(yr) for yr in years]))
        # print(f"{date} => {years} =>{centuries}")
        return centuries
    return None #'no_valide_date' 

def explod_deduplicate_df_by_col(df, col_dedup="vrai_folio",col_exploded="date_propre"):
    if col_dedup not in df.columns:
        df[col_dedup]=df.folio+"_"+df.manuscrit

    print(f'len avant déduplication selon {col_dedup}:{len(df)}')
    df=df.drop_duplicates(subset=col_dedup)
    print(f'après:{len(df)}\n')


    print(f"len avant 'explode' selon {col_exploded}: {len(df)}")    
    df_exploded=df.explode(column=col_exploded)
    print(f"après: {len(df_exploded)}")    

    return df_exploded




def plot_frequent(df,top_n=None, col="lieu_propre", to_dropna=True):
    plt.figure(figsize=(8,6))
    if to_dropna==True:
        df=df[df[col].notna()]

    if top_n is not None:
        top_df = df[col].value_counts().nlargest(top_n).index

        plt.figure(figsize=(8, 6))
        sns.countplot(
            data=df[df[col].isin(top_df)], 
            y=col, 
            order=top_df,
            palette='viridis'
        )
        plt.title(f"Répartition de top{top_n} de {col}")
        plt.show()
        
    else :
        df=df.sort_values(by=col, ascending=False)
        # y_min=int(df[col].min())
        # y_max=int(df[col].max())
        # order = list(range(y_min, y_max))
        order = list(range(1, 21))

        sns.countplot(data=df, y=col,order=order,palette='viridis')
        plt.title(f"Répartition de {col}")
        plt.show()    

    return 


def preprocess_loc_date(df,output_path="data/gallica_data_cheval_propre.csv"):

    print(f"=====================nettoyer les données================\n"
          f"- lieu=> novelle col: lieu propre:\n"
          f"si parenthèse+pas une position : prend le lieu entre parenthèses;\n"
          f"si parenthèse + une position : prend ce qui est devant parenthèses;\n"
          f"pas de parenthèse: prend ce qui est devant le virgule.\n\n"
          
          f'- date=> nouvelle col: date propre:\n'
          f"si dates romaines : transformer en chiffre arabes, et puis en sicèle XX;\n"
          f"si dates arabes au forme de XXXX, extraire XXXX, les transforme en siècles XX\n"
          f'si multi sicèles [XX, XX], exploser les données, cad compter n fois cette ligne.\n'
          f"si date invalide, labelisé par'no_valide_date'")

    start_time=time.time()
    # lieu.
    print('---------------------lieu-------------------')
    df['lieu_propre'] = df['lieu'].progress_apply(extract_loc)

    # df['lieu_propre']=df['lieu'].apply(extract_loc)
    print(df.lieu_propre.value_counts(dropna=False),"\n")

    #date:
    print('---------------------date-------------------')
    df['date_propre']=df['date'].progress_apply(extract_date)
    # print(df.date_propre.value_counts().sort_values(ascending=False),"\n")

    print('----------------dedeup+explode------------------')    
    df_exploded=explod_deduplicate_df_by_col(df, col_exploded="date_propre", col_dedup="vrai_folio")
    print(df_exploded.date_propre.value_counts(dropna=False).sort_values(ascending=False),"\n")
    

    #plot
    plot_frequent(df_exploded, col='date_propre')
    plot_frequent(df_exploded,top_n=10, col="lieu_propre")

    #save:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_exploded.to_csv(output_path,index=False)
    print(f"\n[SAVE] CSV nettoyé sauvegardé dans {output_path}!")

    # time:
    end_time=time.time()
    print(f"\n[SUCCES] data processed in {end_time-start_time:.2f} sec!")
    return df_exploded


