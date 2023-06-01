import pandas as pd
import numpy as np
import streamlit as st
from io import BytesIO
from zipfile import ZipFile

def true_score(difficulty,logits,inf=-5.0,sup=5.0):
    if not logits:
        difficulty = (difficulty-500)/100
    ni = difficulty.shape[0]
    hab = np.arange(inf,sup + 0.001,0.001)
    d,b = np.meshgrid(difficulty,hab)
    p = np.sum(np.exp(b-d)/(1+np.exp(b-d)),axis=1)
    idx = np.round(p-0.5,0)
    idx = (np.concatenate([[-1],idx]) != np.concatenate([idx,[ni]]))[:-1]
    df = pd.DataFrame({'Escala':hab[idx],'PuntajeAprox':p[idx]})
    last = pd.DataFrame({'Escala':[sup],'PuntajeAprox':[ni]})
    df = pd.concat([df,last],ignore_index=True)
    return df

def tablas_eq(df,proceso,logit):
    l = []
    for comp in df['Competencia'].unique():
        measures = df.loc[df['Competencia']==comp,'Medición']
        measures = measures.fillna(measures.mean())
        score = true_score(measures.to_numpy(),logits=logit)
        score['PuntajeAprox'] = score['PuntajeAprox'].round().astype(int)
        score['Escala'] = score['Escala'].round(3)
        score['Competencia'] = comp
        l.append(score)
    res = pd.concat(l)
    res['Proceso'] = proceso
    return res[['Proceso','Competencia','PuntajeAprox','Escala']]

def tablas_ep(df,proceso,logit):
    df['Proceso'] = proceso
    if not logit:
        df['Medición'] = ((df['Medición']-500)/100)
        df['Error'] = (df['Error']/100)
    df['Medición'] = df['Medición'].round(3)
    df['Error'] = df['Error'].round(3)
    if (df['Error'] < 0).any():
        print('Error no puede ser negativo!')
    return df[['Proceso','CodPregunta OCA','Medición','Error']]

def generarTablas(archivos,logit):
    procesos = {}
    for archivo in archivos:
        df = pd.read_excel(archivo,header=None)
        proceso = df.iloc[0,1]
        prueba = df.iloc[1,1]
        if proceso not in procesos:
            procesos[proceso] = {}
        procesos[proceso][prueba] = {}
        df = pd.read_excel(archivo,skiprows=2)
        df['Competencia'] = df['Competencia'].astype(str).str.zfill(3)
        procesos[proceso][prueba]['TEQ'] = tablas_eq(df,prueba,logit)
        procesos[proceso][prueba]['TEP'] = tablas_ep(df,prueba,logit)
    return procesos

def resumen(procesos):
    tabs = st.tabs(procesos.keys())
    for i,proceso in enumerate(procesos.keys()):
        with tabs[i]:
            subtabs = st.tabs(procesos[proceso].keys())
            for j,prueba in enumerate(procesos[proceso].keys()):
                with subtabs[j]:
                    st.write(procesos[proceso][prueba]['TEP'])
                    st.write(procesos[proceso][prueba]['TEQ'])

def zip_tablas(procesos):
    tempZip = BytesIO()
    with ZipFile(tempZip,'w') as zf:
        for proceso,pruebas in procesos.items():
            teqs = []
            teps = []
            for prueba,tablas in pruebas.items():
                teqs.append(tablas['TEQ'])
                teps.append(tablas['TEP'])
            teq = pd.concat(teqs,ignore_index=True)
            with zf.open(f'{proceso}_cargaTEQ.txt','w') as teqBuffer:
                teq.to_csv(teqBuffer,header=None,index=None,lineterminator='\r\n',float_format='%.3f',encoding='utf8')
            tep = pd.concat(teps,ignore_index=True)
            with zf.open(f'{proceso}_cargaEP.txt','w') as tepBuffer:
                tep.to_csv(tepBuffer,header=None,index=None,lineterminator='\r\n',float_format='%.3f',encoding='utf8')
    st.download_button("Descargar tablas",data=tempZip.getvalue(),file_name='Tablas.zip',mime="application/zip")
    tempZip.close()

def main():
    st.title("Generar tablas DTI")
    with st.sidebar:
        with st.form('archivos'):
            archivos = st.file_uploader("Archivos de estructura",accept_multiple_files=True,help="Seleccionar todos los archivos de estructura cargados a DTI,se agruparán por proceso")
            logit = st.checkbox("Las dificultades están en logits",value=True)
            procesar = st.form_submit_button('PROCESAR')

    if procesar:
        procesos = generarTablas(archivos,logit)
        zip_tablas(procesos)
        resumen(procesos)
        
if __name__ == '__main__':
    main()