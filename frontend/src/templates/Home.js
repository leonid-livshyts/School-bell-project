import React, {useState} from "react";
import '../Home.css';

function Home() {
    
    const [addVoice, setAddVoice] = useState({
        voice: null,
        place: "school",
    });

    let [filename, setFilename] = useState("No file")

    const handleVoiceFileChange = (event) => {
        setAddVoice((prev) => ({ ...prev, voice: event.target.files[0]}));
        setFilename(event.target.files[0].name)
    };
    const handleVoicePlaceChange = (event) => {
        setAddVoice((prev) => ({ ...prev, place: event.target.value}));
    };

    async function add_voice(event) {
        event.preventDefault();

        if (!addVoice.voice) {
            alert("Будь ласка, виберіть файл");
            return;
        }

        const formData = new FormData();
        formData.append("file", addVoice.voice);

            try {
                const response = await fetch(`http://10.0.60.208:8080/site/voices/add/${addVoice.place}`, {
                    method: 'POST',
                    body: formData,
                    credentials: "include"
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
        
    }

    return (
        <main>
            <section className="voice">
                <h1>Промовити промову</h1>
                <form name="play_ringtone_form" id="play_ringtone_form" onSubmit={add_voice}>
                    <label className="file_label">Завантажити аудіо промови: {filename}</label>
                    <input type="file" id="voice-upload" name="voice" accept=".mp3,.wav" onChange={handleVoiceFileChange}/>
                    <br/>
                    <label>Виберіть де відбудеться промова</label>
                    <select name="play_ringtone_place" id="play_ringtone_place" onChange={handleVoicePlaceChange}>
                        <option value="school" selected="selected">Усюди</option>
                        <option value="workshop">У Майстерні</option>
                        <option value="201_1">201_1</option>
                        <option value="201_2">201_2</option>
                        <option value="202">202</option>
                        <option value="204">204</option>
                        <option value="205">205</option>
                        <option value="206">206</option>
                        <option value="207">207</option>
                        <option value="208">208</option>
                        <option value="209">209</option>
                        <option value="210">210</option>
                        <option value="211_1">211_1</option>
                        <option value="211_2">211_2</option>
                        <option value="212">212</option>
                        <option value="MHL">Hard lab</option>
                        <option value="MSL">Soft lab</option>
                    </select>
                    <br/>
                    <button type="submit" value="Submit">Промовити</button>
                </form>
            </section>
        </main>
    );
}

export default Home;