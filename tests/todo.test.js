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
<<<<<<< Updated upstream
=======

>>>>>>> Stashed changes
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

// ─── attachButton (buttons.js) ────────────────────────────────────────────────

describe('attachButton', () => {
  beforeEach(setup);

  test('each task item has a .btns container', () => {
    addTask('Check buttons');
    expect(q('.tasks ul li .btns')).not.toBeNull();
  });

  test('each task item has a delete SVG button', () => {
    addTask('Check buttons');
    expect(q('.tasks ul li svg.delete')).not.toBeNull();
  });
});
