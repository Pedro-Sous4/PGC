from __future__ import annotations

import json
import os
from typing import Any, Dict, List

def create_test_index_files() -> None:
    """Create test index files for various frameworks."""
    
    # Create test directory structure
    test_dirs = [
        "test_apps/react_app/src",
        "test_apps/react_app/public",
        "test_apps/vue_app/src",
        "test_apps/vue_app/public",
        "test_apps/angular_app/src",
        "test_apps/nextjs_app/pages",
        "test_apps/nuxt_app/pages",
        "test_apps/svelte_app/src",
        "test_apps/html_js_app",
        "test_apps/python_flask/templates",
        "test_apps/python_django",
        "test_apps/express_app",
        "test_apps/fastapi_app"
    ]
    
    for dir_path in test_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # React App
    create_file("test_apps/react_app/package.json", {
        "name": "react-test-app",
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        }
    })
    
    create_file("test_apps/react_app/src/App.js", '''import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>React Test App</h1>
      </header>
    </div>
  );
}

export default App;''')
    
    create_file("test_apps/react_app/src/index.js", '''import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);''')
    
    create_file("test_apps/react_app/public/index.html", '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>React Test App</title>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>''')
    
    # Vue App
    create_file("test_apps/vue_app/package.json", {
        "name": "vue-test-app",
        "version": "1.0.0",
        "dependencies": {
            "vue": "^3.3.0"
        }
    })
    
    create_file("test_apps/vue_app/src/App.vue", '''<template>
  <div id="app">
    <h1>Vue Test App</h1>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
}
</style>''')
    
    create_file("test_apps/vue_app/src/main.js", '''import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')''')
    
    create_file("test_apps/vue_app/public/index.html", '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Vue Test App</title>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>''')
    
    # Next.js App
    create_file("test_apps/nextjs_app/package.json", {
        "name": "nextjs-test-app",
        "version": "1.0.0",
        "dependencies": {
            "next": "^13.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        }
    })
    
    create_file("test_apps/nextjs_app/pages/index.js", '''export default function Home() {
  return (
    <div>
      <h1>Next.js Test App</h1>
    </div>
  )
}''')
    
    # Nuxt App
    create_file("test_apps/nuxt_app/package.json", {
        "name": "nuxt-test-app",
        "version": "1.0.0",
        "dependencies": {
            "nuxt": "^3.0.0"
        }
    })
    
    create_file("test_apps/nuxt_app/pages/index.vue", '''<template>
  <div>
    <h1>Nuxt Test App</h1>
  </div>
</template>''')
    
    # Svelte App
    create_file("test_apps/svelte_app/package.json", {
        "name": "svelte-test-app",
        "version": "1.0.0",
        "dependencies": {
            "svelte": "^4.0.0"
        }
    })
    
    create_file("test_apps/svelte_app/src/App.svelte", '''<script>
  let name = 'Svelte';
</script>

<main>
  <h1>Svelte Test App</h1>
</main>

<style>
  main {
    text-align: center;
    padding: 1em;
  }
</style>''')
    
    # HTML/JS App
    create_file("test_apps/html_js_app/index.html", '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTML/JS Test App</title>
</head>
<body>
    <div id="app">
        <h1>HTML/JavaScript Test App</h1>
        <p id="message">Loading...</p>
    </div>
    <script src="app.js"></script>
</body>
</html>''')
    
    create_file("test_apps/html_js_app/app.js", '''document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('message').textContent = 'JavaScript is working!';
});''')
    
    # Flask App
    create_file("test_apps/python_flask/requirements.txt", '''Flask==2.3.0
Jinja2==3.1.0''')
    
    create_file("test_apps/python_flask/app.py", '''from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', title='Flask Test App')

if __name__ == '__main__':
    app.run(debug=True)''')
    
    create_file("test_apps/python_flask/templates/index.html", '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Flask is working!</p>
</body>
</html>''')
    
    # Django App
    create_file("test_apps/python_django/requirements.txt", '''Django==4.2.0''')
    
    create_file("test_apps/python_django/manage.py", '''#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_test_app.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()''')
    
    # Express App
    create_file("test_apps/express_app/package.json", {
        "name": "express-test-app",
        "version": "1.0.0",
        "dependencies": {
            "express": "^4.18.0"
        }
    })
    
    create_file("test_apps/express_app/app.js", '''const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
  res.send('<h1>Express Test App</h1><p>Express is working!</p>');
});

app.listen(port, () => {
  console.log(`Express app listening at http://localhost:${port}`);
});''')
    
    # FastAPI App
    create_file("test_apps/fastapi_app/requirements.txt", '''fastapi==0.104.0
uvicorn==0.24.0''')
    
    create_file("test_apps/fastapi_app/main.py", '''from fastapi import FastAPI

app = FastAPI(title="FastAPI Test App")

@app.get("/")
def read_root():
    return {"message": "FastAPI Test App", "status": "working"}''')

def create_file(filepath: str, content: Any) -> None:
    """Helper function to create files with proper formatting."""
    if isinstance(content, dict):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(content))

if __name__ == "__main__":
    create_test_index_files()
    print("Test index files created successfully!")