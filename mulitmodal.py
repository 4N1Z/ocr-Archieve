import PIL,os
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter;
from langchain_chroma import Chroma 
from langchain_core.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain
from pprint import pprint
import warnings

warnings.filterwarnings("ignore")
# genai.configure(api_key="AIzaSyD8upeBZp28kN9eOhFZ-NDR-UfvPH1U_8Q")
google_api_key='AIzaSyD8upeBZp28kN9eOhFZ-NDR-UfvPH1U_8Q'
genai.configure(api_key=google_api_key)
model = genai.GenerativeModel('models/gemini-pro')
text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=0)

def simpleGemini() :

    with open('predictions.txt', 'r') as file:
        contents = file.read()
    # print(contents)
    result = model.generate_content([ "Who is the patient and wht are the medications told? also specify the page in which it is :", contents])
    print(result.text)



def googleEmbedings():

    with open('predictions.txt', 'r') as file:
        contents = file.read()

    prompt_template = """Answer the question as precise as possible using the provided context. If the answer is
                    not contained in the context, say "answer not available in context" \n\n
                    Context: \n {context}?\n
                    Question: \n {question} \n
                    Answer:
                  """

    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    # stuff_chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)


    
    texts = text_splitter.split_text(contents)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_index = Chroma.from_texts(texts, embeddings).as_retriever()

    question = "What is this? give a detailed description "
    docs = vector_index.get_relevant_documents(question)
    print(docs)


    # stuff_answer = stuff_chain(
    # {"input_documents": docs, "question": question}, return_only_outputs=True)

    # pprint(stuff_answer)




googleEmbedings()

