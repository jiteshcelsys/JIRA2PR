/**
 * Tests for the ToDo App (app/app.js + app/buttons.js)
 *
 * Strategy: set up the HTML in jsdom, eval both scripts so their event
 * listeners attach to the live DOM nodes, then simulate user interactions
 * via dispatched events and assert DOM state.
 */

const fs = require('fs');
const path = require('path');

const buttonsScript = fs.readFileSync(path.resolve(__dirname, '../app/buttons.js'), 'utf8');
const appScript = fs.readFileSync(path.resolve(__dirname, '../app/app.js'), 'utf8');

const HTML = `
  <div class="wrapper">
    <div class="app">
      <input type="text" id="task" placeholder="Add Your Task Here" class="task">
      <div class="lists">
        <section class="favs"><h3></h3><ul></ul></section>
        <section class="tasks"><h3></h3><ul></ul></section>
        <section class="done"><h3></h3><ul></ul></section>
      </div>
    </div>
    <footer><p>&copy;2026 Jitesh Pandey. All Rights Reserved</p></footer>
  </div>
`;

function setup() {
  document.body.innerHTML = HTML;
  window.alert = jest.fn();
  // eval loads the scripts into the current jsdom context so their
  // event listeners attach to the live DOM elements above.
  // eslint-disable-next-line no-eval
  eval(buttonsScript);
  // eslint-disable-next-line no-eval
  eval(appScript);
}

/** Press Enter in the task input with the given value */
function addTask(value) {
  const input = document.querySelector('input.task');
  input.value = value;
  input.dispatchEvent(new KeyboardEvent('keyup', { keyCode: 13, bubbles: true }));
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const q = (sel) => document.querySelector(sel);

// ─── Initial state ────────────────────────────────────────────────────────────

describe('Initial state', () => {
  beforeEach(setup);

  test('tasks section is hidden when there are no tasks', () => {
    expect(q('.tasks').style.display).toBe('none');
  });

  test('favs section is hidden when there are no favourites', () => {
    expect(q('.favs').style.display).toBe('none');
  });
});

// ─── Adding tasks ─────────────────────────────────────────────────────────────

describe('Adding a task', () => {
  beforeEach(setup);

  test('pressing Enter adds a task to the list', () => {
    addTask('Buy groceries');
    expect(q('.tasks ul').children.length).toBe(1);
    expect(q('.tasks ul li').textContent).toContain('Buy groceries');
  });

  test('tasks section becomes visible after adding a task', () => {
    addTask('Test task');
    expect(q('.tasks').style.display).not.toBe('none');
  });

  test('tasks section heading is set to "Inbox"', () => {
    addTask('Test task');
    expect(q('.tasks h3').textContent).toBe('Inbox');
  });

  test('input is cleared after adding a task', () => {
    addTask('Test task');
    expect(q('input.task').value).toBe('');
  });

  test('pressing a key other than Enter does not add a task', () => {
    const input = q('input.task');
    input.value = 'Ignored';
    input.dispatchEvent(new KeyboardEvent('keyup', { keyCode: 65, bubbles: true })); // 'a'
    expect(q('.tasks ul').children.length).toBe(0);
  });

  test('multiple tasks can be added', () => {
    addTask('Task one');
    addTask('Task two');
    addTask('Task three');
    expect(q('.tasks ul').children.length).toBe(3);
  });
});

// ─── Empty-task validation ────────────────────────────────────────────────────

describe('Empty-task validation', () => {
  beforeEach(setup);

  test('shows an alert when trying to add an empty task', () => {
    addTask('');
    expect(window.alert).toHaveBeenCalledWith('Please add a task');
  });

  test('does not add an empty task to the list', () => {
    addTask('');
    expect(q('.tasks ul').children.length).toBe(0);
  });
});

// ─── Deleting tasks ───────────────────────────────────────────────────────────

describe('Deleting a task (click on SVG element)', () => {
  beforeEach(() => {
    setup();
    addTask('Task to delete');
  });

  test('clicking the delete SVG removes the task', () => {
    q('.tasks ul li svg.delete').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks ul').children.length).toBe(0);
  });

  test('tasks section is hidden after the last task is deleted', () => {
    q('.tasks ul li svg.delete').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks').style.display).toBe('none');
  });
});

describe('Deleting a task (click on inner path element)', () => {
  beforeEach(() => {
    setup();
    addTask('Task to delete via path');
  });

  test('clicking the cap path removes the task', () => {
    q('.tasks ul li path.cap').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks ul').children.length).toBe(0);
  });

  test('clicking the can path removes the task', () => {
    // Re-add since the previous test already removed it (each beforeEach re-adds)
    q('.tasks ul li path.can').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks ul').children.length).toBe(0);
  });
});

// ─── Favouriting tasks ────────────────────────────────────────────────────────

describe('Favouriting a task (click on SVG element)', () => {
  beforeEach(() => {
    setup();
    addTask('Favourite this task');
  });

  test('clicking the fav SVG moves the task to the favourites list', () => {
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs ul').children.length).toBe(1);
    expect(q('.tasks ul').children.length).toBe(0);
  });

  test('favs section becomes visible after favouriting', () => {
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs').style.display).not.toBe('none');
  });

  test('favs section heading is set to "Favorites"', () => {
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs h3').textContent).toBe('Favorites');
  });

  test('tasks section is hidden after the only task is favourited', () => {
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks').style.display).toBe('none');
  });
});

describe('Favouriting a task (click on inner path element)', () => {
  beforeEach(() => {
    setup();
    addTask('Favourite via path');
  });

  test('clicking the favPath path moves the task to favourites', () => {
    q('.tasks ul li path.favPath').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs ul').children.length).toBe(1);
    expect(q('.tasks ul').children.length).toBe(0);
  });
});

// ─── Un-favouriting tasks ─────────────────────────────────────────────────────

describe('Un-favouriting a task', () => {
  beforeEach(() => {
    setup();
    addTask('Toggle me');
    // Move to favourites first
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });

  test('clicking fav SVG on a favourite moves it back to the inbox', () => {
    q('.favs ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks ul').children.length).toBe(1);
    expect(q('.favs ul').children.length).toBe(0);
  });

  test('tasks section heading is restored to "Inbox" when un-favouriting', () => {
    q('.favs ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.tasks h3').textContent).toBe('Inbox');
  });

  test('favs section is hidden after the last favourite is removed', () => {
    q('.favs ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs').style.display).toBe('none');
  });
});

// ─── Deleting from favourites ─────────────────────────────────────────────────

describe('Deleting a task from the favourites section', () => {
  beforeEach(() => {
    setup();
    addTask('Delete from favs');
    q('.tasks ul li svg.fav').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });

  test('clicking delete SVG in favs removes the task', () => {
    q('.favs ul li svg.delete').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs ul').children.length).toBe(0);
  });

  test('favs section is hidden after the last favourite is deleted', () => {
    q('.favs ul li svg.delete').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    expect(q('.favs').style.display).toBe('none');
  });
});

// ─── attachButton (buttons.js) ────────────────────────────────────────────────

describe('attachButton', () => {
  beforeEach(setup);

  test('each task item has a .btns container', () => {
    addTask('Check buttons');
    expect(q('.tasks ul li .btns')).not.toBeNull();
  });

  test('each task item has a favourite SVG button', () => {
    addTask('Check buttons');
    expect(q('.tasks ul li svg.fav')).not.toBeNull();
  });

  test('each task item has a delete SVG button', () => {
    addTask('Check buttons');
    expect(q('.tasks ul li svg.delete')).not.toBeNull();
  });
});
