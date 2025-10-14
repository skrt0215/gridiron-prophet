# Gridiron Prophet

Gridiron Prophet is a program that has been trained to analyze, process, and predict the scores of past, present, and future games for the NFL. It has been trained with a sample size spanning four seasons (755+ games!), injury reports, player trends, and MUCH MORE to give you the most accurate recommendation while also deciding on which side of the ball to bet on based on Vegas odds. 

## Usage
- The first iteration if the streamlit version for this applcation has been developed and is currently undergoing optimization to ensure the best experience utilizing the application.
- It will be using ngrok for port forwarding and enabling numerous users to access the site to use its features and log their own picks.
- Upon full completion of accurate training and rosters across the league, this program will be able to enter the test phases with numerous users.

## Features
- Predictive models for game outcomes
- Spread analyzer for betting predictions
- Live injury report tracking
- Confidence level in bets
- Live training weekly after games are had
- Head to head! Choose two teams to face off for the bot to make a determination based off of its own thought process!

## Tech Stack
- Python 3.11+ (REQUIRED)
- Pandas, NumPy (Data Analysis)
- Scikit-learn (Machine Learning)
- Streamlit, ngrok (Visualization)
- MySQL (Data Entry and Storage)

## Roadmap
- [x] Set up project structure and database schema
- [x] Create database connection and management system
- [x] Populate database with NFL teams
- [x] Build data collection pipeline for historical games
- [x] Fetch current season game data and stats
- [x] Implement injury tracking system
- [x] Add depth chart data collection
- [x] Integrate betting odds APIs
- [x] Build initial prediction models
- [ ] Create player performance analytics
- [x] Develop visualization dashboard
- [x] Backtesting framework for model validation
- [x] Real-time prediction system
- [ ] Real-time analysis post game for accuracy in training
- [ ] Weather forecast to implement into the decision process
- [x] Weekly generated report
- [x] Optimized streamlit site for public usage and better interaction
