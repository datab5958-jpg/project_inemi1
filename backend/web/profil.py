from flask import Blueprint, render_template, jsonify, session, redirect, url_for

profil_bp = Blueprint('profil', __name__)

@profil_bp.route('/profil')
def profil_page():
    return render_template('profile.html')

@profil_bp.route('/api/user/profile')
def api_user_profile():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    # TODO: Ganti data dummy dengan data user dari database
    return jsonify({
        "full_name": "Budi Santoso",
        "username": "budi123",
        "profile_pic": "/logo/logo.png",
        "bio": "AI enthusiast. Suka musik dan teknologi.",
        "token": 42
    })

@profil_bp.route('/api/user/activity-log')
def api_user_activity_log():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    # TODO: Ganti data dummy dengan data user dari database
    return jsonify({
        "music": [
            {"name": "Cinta Terbaik", "date": "2024-06-01", "thumbnail": "/photo_results/21e2964637134834a5c01d2531dc4be4.png"},
            {"name": "Senja Merah", "date": "2024-05-30", "thumbnail": "/photo_results/2adc567a7fb046b9beab434c94d39531.png"},
            {"name": "Harmoni Alam", "date": "2024-05-28", "thumbnail": "/photo_results/37aba1eb9a2b451ab9769d01657888bf.png"}
        ],
        "photo": [
            {"name": "Upacara Bendera", "date": "2024-06-01", "thumbnail": "/photo_results/47e00dd0d40645e5b219b086f125fa3c.png"},
            {"name": "Pemandangan Sawah", "date": "2024-05-29", "thumbnail": "/photo_results/50f91a995288419396e99f65e24f17e4.png"},
            {"name": "Gunung Pagi", "date": "2024-05-27", "thumbnail": "/photo_results/512f3466a95f46fa93f70f0c7cc7f83f.png"}
        ],
        "video": [
            {"name": "Upacara 17an", "date": "2024-06-01", "thumbnail": "/output.png"},
            {"name": "Senja di Kota", "date": "2024-05-30", "thumbnail": "/output.png"},
            {"name": "Pagi di Gunung", "date": "2024-05-28", "thumbnail": "/output.png"}
        ]
    }) 