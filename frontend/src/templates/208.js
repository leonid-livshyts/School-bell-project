import { useEffect, useState } from "react";
import React from "react";
import '../App.css';
import SensorCharts from "../sensorChart.js";

const bell_id = "208";
const url = '10.0.60.208:8080'
const calendar_i = "https://calendar.google.com/calendar/embed?src=c6b3d4731c97d4a390cce0c2d5d4ecefe80d4426977569fb8ff5d2563ef4396a%40group.calendar.google.com&ctz=Europe%2FKiev"

function R208() {

    let [filename, setFilename] = useState("No file")

    const readFilename = (event) => {
        setFilename(event.target.files[0].name)
    }
    
    const fetchLastMelody = async () => {
        try {
          const res = await fetch(`http://${url}/site/get_last_melody/${bell_id}`);
          const data = await res.json();
          const melodyName = data.last_uploaded_melody ? data.last_uploaded_melody : 'Немає мелодії';
          document.getElementById('melody-name').innerText = melodyName;
        } catch (error) {
          console.error("Помилка при отриманні даних:", error);
        }
      };


    
    async function handleUpload(event) {
        event.preventDefault();
    
        let formData = new FormData(event.target);
        try {
            const response = await fetch(`http://${url}/site/bells/upload_melody/${bell_id}`, {
                method: 'POST',
                body: formData
            });
            let res = await response.json()

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            };

        
            alert(res.message || "File uploaded successfully!");

        } catch (error) {
            console.error("Error uploading file:", error);
            alert("Failed to upload file.");
        }
    fetchLastMelody();
    }
            
    window.onload = fetchLastMelody;
    useEffect(() => {
        fetchLastMelody();
    }, []);
    return (
        <main>
            <div id="text_cont"><h1>Сторінка дзвінка {bell_id}</h1></div>
            

            <section id="schedule">
                <div id="schedule_cont">
                    <h2>Розклад уроків</h2>
                    <iframe src={calendar_i} width="1200" height="800" frameborder="0" title="Google Calendar"></iframe>
                </div>
            </section>

            <section id="melodies">
                <h2>Мелодії дзвінка</h2>
                <form id="melody-form" onSubmit={handleUpload} method="post" enctype="multipart/form-data">
                    <label for="melody-upload" className="file_label">Виберіть файл мелодії: {filename}</label>
                    <input type="file" id="melody-upload" name="melody" accept=".mp3,.wav" onChange={readFilename}/>
                    <button type="submit">Оновити мелодію</button>
                </form>
                            
                <div id="last-melody">
                    <h3>Остання завантажена мелодія:</h3>
                    <p id="melody-name">Немає мелодії</p>
                </div>
            </section>


            <section id="graphs">
                <h2>Дані з датчиків</h2>
                <SensorCharts bellId={bell_id}/>
            </section>
        </main>
    );
}

export default R208;