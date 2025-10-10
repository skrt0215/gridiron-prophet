#One step process for opening the streamlit visual for the program because I am tired of running terminal commands

echo "🏈 Starting Gridiron Prophet..."
echo "================================"

echo "🗄️  Checking MySQL..."
if ! pgrep -x mysqld > /dev/null; then
    echo "⚠️  MySQL is not running. Starting MySQL server..."
    sudo /usr/local/mysql/support-files/mysql.server start
    sleep 3
else
    echo "✅ MySQL already running"
fi

cd "/Users/steven/Desktop/NFL Game Analyzer/gridiron-prophet"

if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "📦 Checking dependencies..."
pip install -q streamlit pandas numpy scikit-learn requests pymysql cryptography python-dotenv beautifulsoup4 nfl-data-py lxml html5lib pyngrok 2>/dev/nullecho "✅ Dependencies ready!"

echo "Checking for existing processes on port 8501..."
lsof -ti:8501 | xargs kill -9 2>/dev/null

clear

echo "🚀 Starting Gridiron Prophet..."
echo "================================"
echo ""

streamlit run streamlit_app.py &
STREAMLIT_PID=$!

echo "⏳ Waiting for Streamlit to start..."
sleep 5

echo "Starting ngrok tunnel..."
python start_ngrok.py &
NGROK_PID=$!

echo ""
echo "================================"
echo "✅ Gridiron Prophet is running!"
echo "================================"
echo ""
echo "Public Link:"
sleep 3
curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*' | grep -o 'https://[^"]*' | head -1
echo ""
echo "🔐 Password: Cheesetouch123!"
echo ""
echo "Press Ctrl+C to stop everything"
echo "================================"
wait $STREAMLIT_PID $NGROK_PID