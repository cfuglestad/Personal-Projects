import spotipy
from spotipy.oauth2 import SpotifyOAuth
import numpy as np
from scipy.spatial.distance import cosine
import cred
import pandas as pd
import numpy as np
import schedule
import time
import tkinter as tk
from tkinter import ttk

scope = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"

def get_playlist_names_and_ids(sp):
    playlists = sp.current_user_playlists()
    playlist_info = [(playlist['name'], playlist['id']) for playlist in playlists['items']]
    return playlist_info

def get_playlist_id_by_name(sp, playlist_name):
    playlists_info = get_playlist_names_and_ids(sp)
    for name, id in playlists_info:
        if name == playlist_name:
            return id
    return None

def get_tracks_from_playlist(sp, playlist_id):
    results = sp.playlist_tracks(playlist_id)
    tracks = []
    for item in results['items']:
        track = item['track']
        tracks.append((track['id'], track['name'], [artist['name'] for artist in track['artists']]))
    return tracks

def get_audio_features(sp, track_ids):
    audio_features = sp.audio_features(track_ids)
    return audio_features

def calculate_cosine_similarity(features1, features2):
    return 1 - cosine(features1, features2)

def add_tracks_to_playlist(sp, playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)

def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=cred.CLIENT_ID
                                                   , client_secret= cred.CLIENT_SECRET
                                                   , redirect_uri=cred.REDIRECT_URL
                                                   , scope=scope))

    def run_script():
        # Replace with your chosen playlist name
        chosen_playlist_name = selected_playlist.get()
        discover_weekly_name = "Discover Weekly"
        sorted_playlist_name = "Sorted Discover Weekly"  # Name of the target playlist

        # Get playlist IDs
        chosen_playlist_id = get_playlist_id_by_name(sp, chosen_playlist_name)
        discover_weekly_id = get_playlist_id_by_name(sp, discover_weekly_name)
        sorted_playlist_id = get_playlist_id_by_name(sp, sorted_playlist_name)  # Get the ID of the target playlist

        if not chosen_playlist_id or not discover_weekly_id or not sorted_playlist_id:
            print("One or more playlists not found.")
            return

        # Get track IDs from the chosen playlist
        chosen_playlist_tracks = get_tracks_from_playlist(sp, chosen_playlist_id)

        # Get track IDs from Discover Weekly
        discover_weekly_tracks = get_tracks_from_playlist(sp, discover_weekly_id)

        # Extract audio features for chosen playlist tracks
        chosen_playlist_track_ids = [track[0] for track in chosen_playlist_tracks]
        chosen_playlist_audio_features = get_audio_features(sp, chosen_playlist_track_ids)

        # Create a DataFrame to store track names, artist names, and similarity scores
        track_data = []

        # Loop through Discover Weekly tracks and calculate cosine similarity
        for dw_track in discover_weekly_tracks:
            dw_track_id = dw_track[0]
            dw_track_name = dw_track[1]
            dw_track_artists = ', '.join(dw_track[2])  # Join multiple artists with a comma
            dw_track_audio_features = get_audio_features(sp, [dw_track_id])[0]

            if dw_track_audio_features:
                similarity = calculate_cosine_similarity(
                    np.array([dw_track_audio_features['acousticness']
                            , dw_track_audio_features['danceability']
                            , dw_track_audio_features['energy']
                            , dw_track_audio_features['valence']
                            , dw_track_audio_features['instrumentalness']
                            , dw_track_audio_features['liveness']
                            , dw_track_audio_features['loudness']
                            , dw_track_audio_features['speechiness']
                            , dw_track_audio_features['tempo']
                            , dw_track_audio_features['key']]),  # Add more features here
                    np.array([chosen_playlist_audio_features[0]['acousticness']
                            , chosen_playlist_audio_features[0]['danceability']
                            , chosen_playlist_audio_features[0]['energy']
                            , chosen_playlist_audio_features[0]['valence']
                            , chosen_playlist_audio_features[0]['instrumentalness']
                            , chosen_playlist_audio_features[0]['liveness']
                            , chosen_playlist_audio_features[0]['loudness']
                            , chosen_playlist_audio_features[0]['speechiness']
                            , chosen_playlist_audio_features[0]['tempo']
                            , chosen_playlist_audio_features[0]['key']])  # Replace with chosen playlist track's features
                )
                track_data.append((dw_track_name, dw_track_artists, similarity, dw_track_id))  # Store track name, artist names, similarity score, and track ID

        # Create a DataFrame from the track data
        df = pd.DataFrame(track_data, columns=['Track Name', 'Artist Names', 'Similarity Score', 'Track ID'])

        # Sort the DataFrame by similarity score in descending order
        df = df.sort_values(by='Similarity Score', ascending=False)

        # Return the track IDs of the sorted tracks
        sorted_track_ids = df['Track ID'].tolist()

        # Clear the existing tracks in the sorted playlist
        sp.playlist_remove_all_occurrences_of_items(sorted_playlist_id, sorted_track_ids)

        # Add the sorted tracks to the sorted playlist
        add_tracks_to_playlist(sp, sorted_playlist_id, sorted_track_ids)

        print(f"Playlist '{sorted_playlist_name}' updated with sorted tracks.")

    root = tk.Tk()
    root.title("Playlist Selection")

    # Get user's playlists
    playlist_names = [name for name, _ in get_playlist_names_and_ids(sp)]

    # Create a Tkinter StringVar to store the selected playlist name
    selected_playlist = tk.StringVar()

    # Create a label
    label = tk.Label(root, text="Select a playlist:")
    label.pack()

    # Create a dropdown list with a default value of "Country"
    selected_playlist.set("Country")
    dropdown = ttk.Combobox(root, textvariable=selected_playlist, values=playlist_names)
    dropdown.pack()

    # Create a button to run the script
    run_button = tk.Button(root, text="Run Script", command=run_script)
    run_button.pack()

    def default_selection():
        if not selected_playlist.get():
            selected_playlist.set("country")
        run_script()

    # Set a timer to run the script with the default selection after 20 seconds
    root.after(20000, default_selection)

    root.mainloop()

if __name__ == "__main__":
    # Schedule the script to run every Monday at noon
    schedule.every().monday.at("12:00").do(main)

    # Run the script continuously
    while True:
        schedule.run_pending()
        time.sleep(1)