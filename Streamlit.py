import re

import pandas as pd
import requests
import streamlit as st
from openai import AzureOpenAI
import plotly
import matplotlib


client = AzureOpenAI(
    azure_endpoint="https://openai-projectaz-2024.openai.azure.com/",
    api_key="6539fe25829b4127b162e6e827af43e5",
    api_version="2024-02-15-preview"
)

# Max data length before GPT does weird things
MAX_LENGTH = 116


def log_messages(object_name, message, state):
    if state == 'error':
        message = f":red[**{message}**]"
    if state == 'complete':
        message = f":green[{message}]"
    if state == 'warning':
        message = f":orange[{message}]"
        state = 'error'
    object_name.write(message)
    object_name.update(label=message, state=state)


def ask_open_ai(openai_question):
    file = open("debug/prompt.txt", "a")
    file.write(openai_question + " \n\n-------------------------------------------------------------------- \n")
    file.close()

    query_response = client.chat.completions.create(
        model="Gilles-gpt-model",
        messages=[{"role": "system",
                   "content": "From the user you will receive data and you need to create visualisations with "
                              "streamlit code that is compatible with version 1.33.0 \n It is crucial you put the code between ```\nPut code here\n```  "},

                  # Opdracht
                  {"role": "user",
                   "content": openai_question}],
        temperature=0
    )

    # Get the content of the response
    this_reply = query_response.choices[0].message.content

    code_pattern = re.compile(r"(?:```(?:python)?\s*|<code>)(.*?)\s*(?:```|</code>)", flags=re.DOTALL | re.IGNORECASE)

    code_match = code_pattern.search(this_reply)

    # If a code block is found, extract it
    this_note = code_pattern.sub('', this_reply).strip()

    # If a code block is found, extract it
    this_code = None
    if code_match:
        this_code = code_match.group(1).strip()

    return this_note, this_code, this_reply

# Function to calculate the number of tokens in a string
def count_tokens(text):
    if isinstance(text, str):
        return len(text.split())
    else:
        return 0


# Function to trim data to fit within the token limit

def trim_data(data):
    total_tokens = sum(sum(count_tokens(value) for value in item.values()) for item in data)
    
    
    if total_tokens > MAX_LENGTH:
        
        
        # Calculate how many tokens to trim
        tokens_to_trim = total_tokens - MAX_LENGTH
        
        # Sort the items by token count (descending order)
        sorted_data = sorted(data, key=lambda item: sum(count_tokens(value) for value in item.values()), reverse=True)
        
        # Trim items until the total token count is within the limit
        trimmed_data = []
        current_tokens = 0
        for item in sorted_data:
            item_tokens = sum(count_tokens(value) for value in item.values())
            if current_tokens + item_tokens <= MAX_LENGTH:
                trimmed_data.append(item)
                current_tokens += item_tokens
            else:
                # If adding this item exceeds the limit, break the loop
                break
                
        log_messages(status_bar, f"Data exceeded maximum GPT token limit and was trimmed to {len(trimmed_data)}", "warning")
        return trimmed_data
    
    return data  # Return the original data list if no trimming is necessary








st.set_page_config(
    page_title="Explore the Skies",
    page_icon="✈️✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Welcome!")
st.subheader("Explore the Skies: Unleash the Power of Open Flights Data")
st.markdown(
    "Welcome to your one-stop shop for exploring the world of aviation! We have unlocked the vast treasure trove of "
    "Open Flights Data, putting the power of information at your fingertips. Curious about aircraft types, "
    "specific airlines, or flight routes?  Ask away!  Whether you\'re a seasoned traveler, an aviation enthusiast, "
    "or simply seeking knowledge, this data is ready to answer your questions. Don't hesitate to delve into details "
    "like departure times, destinations, and even aircraft configurations.\n"
    "You can also specify which graphs you want to see, and otherwise GPT will be creative and create some graphs for you!")
st.write("**Based on data. Made by Gilles. Created for algorythm. Built with trust.**")
st.divider()
user_input = st.text_input('So what questions do you have about the world of flights today? (e.g: Show me 15 flights and a graph that shows the departure candidates count)')

if user_input:
    # Connecting to Database API
    status_bar = st.status("Connecting to Database API")
    test_response = requests.get(f"https://api-az-project.azurewebsites.net/")
    log_messages(status_bar, "Checking API status", "running")
    # Check for response
    if test_response:
        log_messages(status_bar, f"API is responding: {test_response}", "running")
        log_messages(status_bar, "Gathering data from our API", "running")
        response = requests.get(f"https://api-az-project.azurewebsites.net/call?input={user_input}")

        data = response.json()
        
        log_messages(status_bar, "Succesfully connected to the API", "complete")
        
    
        # Trim the data list to fit within the token limit
        data['data'] = trim_data(data['data'])
        
       


        # Ask GPT for visualisations
        status_bar2 = st.status("Creating smart visualisations")
        log_messages(status_bar2, "Creating smart visualisations", "running")

        question = (
            f"Write Streamlit version 1.33.0 code that creates some nice visualization. \n"
            f"This is what the user asks: {user_input}"
            f"If for example the user only asks to show 10 aircrafts you can be creative and also add some graphs, boxplots and visualisations for example. The installed modules are pandas, ploty, streamlit and matplotlib"
            f"Use only Streamlit code and nothing else. Put the code between <code>Put code here</code>"
            f"This is the data to creates some nice visualization on: {data} \n ")

        f = open("debug/prompt.txt", "w")
        f.write("In this file you will find the prompts that are sent to ChatGPT: \n\n")
        f.close()

        status_bar3 = st.status("Executing the visualisations")
        log_messages(status_bar3, "Executing the visualisations", "running")

        st.title("Query to be executed")
        st.write("This is the GPT generated query that our database will use to request the data")
        st.code(data['query'])
        
       

        note, code, reply = ask_open_ai(question)

        # Create debug files
        f = open("debug/note.txt", "w")
        f.write("In this file you will find all the notes that ChatGPT created: \n")
        f.close()
        f = open("debug/code.txt", "w")
        f.write("In this file you will find all the code that ChatGPT created: \n")
        f.close()

        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            attempts += 1

            log_messages(status_bar2, "Analyzing visualisation code", "running")

            try:
                log_messages(status_bar2, "Succesfully created the visualisation code", "complete")

                f = open("debug/note.txt", "a")
                f.write("\n" + "--------------------------------------------------" + "\n" + f"This is the generated note during attempt {attempts}: \n" + str(note) + "\n\n" + "\n" + "--------------------------------------------------" + "\n\n" )
                f.close()
                f = open("debug/code.txt", "a")
                f.write(code)
                f.close()

                # Run the code
                exec(str(code))

                log_messages(status_bar3, "Succesfully created visualisations", "complete")
                attempts = 10
                break

            except Exception as e:
                log_messages(status_bar3,
                             f"During attempt {attempts}, there was an error during execution: {str(e)}",
                             "error")

                # Now you can pass the error message back to OpenAI for a retry.
                question = f"Fix this Exception: {str(e)} in this code {code} Here is all the data {question}"
                log_messages(status_bar3, f"Asking GPT to solve the error", "running")
                note, code, reply = ask_open_ai(question)

                f = open(f"debug/code.txt", "a")
                f.write(f"\n\nThis is the generated code during attempt {attempts} :" + str(
                    code) + f"\nError that should be solved: {str(e)}" + "\n\n")
                f.close()


                if attempts == max_attempts:
                    log_messages(status_bar3, f"Asking GPT for the last time", "running")

                    question = (f"This is the data variable that I am using: <data>{data}</data> just create a "
                                f"very basic table and convert to dataframe")
                    note, code, reply = ask_open_ai(question)

                    log_messages(status_bar3,
                                 "Max retry attempts reached. Unable to create visualisation, showing standard dataframe.",
                                 "error")
                    
                    st.title("Table view")
                    st.write("This is a standard table with all the data you requested")
                    
                    df = pd.DataFrame(data['data'])
                    st.write(df)

                   

                    st.title("This is the code that GPT generated")
                    st.code(str(code))
                    exec(str(code))
                    break  # Exit the loop if max attempts reached

        if not code:
            f = open("debug/note.txt", "a")
            f.write("No visualization created because there is no code to be found, trying again" + reply)

            f.close()

            log_messages(status_bar2, f"No visualization created because there is no code to be found", "error")
            log_messages(status_bar3, f"Code execution cancelled, showing precoded dataframe", "error")

            df = pd.DataFrame(data['data'])
            st.write(df)


    # NO API response
    else:
        log_messages(status_bar, f"API is not responding, no data retrieved. Status code: {test_response}", "error")
