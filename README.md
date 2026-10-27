# Voting Platform — Sprint 3 (all features)

> **Team project.** Built with a team for the "IT Agile Development" course
> (University of Europe for Applied Sciences), following Scrum (sprints,
> Jira-tracked backlog). This repo is the merged Sprint 3 feature set.

University project for IT Agile Development. Django REST + React platform with
the full Sprint 3 feature set merged together:

| Feature | Epic |
|---|---|
| WhatsApp Chat Frequency & Sentiment Analysis | SCRUM-11 |
| Dataset Import / Export (CSV/JSON via Django admin) | SCRUM-3 |
| Meeting Lifecycle Management | SCRUM-13 |
| Smart Notifications (Announcements) + FAQ Chatbot | SCRUM-20 |
| Income/Expense Tracking & Financial Reporting | SCRUM-21 |

## How to run

### Backend (Django, port 8000)
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  |  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt   # installs Django + vaderSentiment
python manage.py migrate
python manage.py seed_faqs        # loads starter FAQs so the FAQ chatbot works
python manage.py createsuperuser  # make an ADMIN account (needed for Meetings/Announcements)
python manage.py runserver
```

> **Admin vs member.** Scheduling Meetings and sending Announcements is
> **admin-only** (same as creating Ballots). Log in with the superuser you
> created above to use those. A normal account (registered from the app) can
> view meetings and read its inbox, but will get "Admin access required" when
> trying to create them — that is by design.

### Frontend (React, port 3000)
```bash
# from the project root, in a second terminal
npm install
npm start
```

`package.json` has `"proxy": "http://127.0.0.1:8000"`, so the React dev server
forwards `/api/*` to Django on a single origin (keeps the session cookie working).
See `RUN_INSTRUCTIONS.txt` for the cookie/session note.

## Try the WhatsApp Chat Analysis (SCRUM-11)

1. Run both servers, open http://localhost:3000, register/log in.
2. Sidebar → **Chat Analysis**.
3. Paste a WhatsApp chat **or** upload a `.txt` export. A ready-made sample is at
   `backend/voting/fixtures/sample_chat_en.txt`.
4. Click **Analyze** → active hours, peak hour, per-participant frequency, and
   positive/negative/neutral sentiment (VADER, English).

Run the feature tests:
```bash
cd backend
python manage.py test voting.tests_chat      # 30 tests
```

More detail: `docs/SCRUM-11-master-plan.md` and `docs/SCRUM-11-INTEGRATION.md`.

---

# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
