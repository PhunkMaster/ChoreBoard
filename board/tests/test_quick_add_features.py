
import pytest
from django.urls import reverse
from chores.models import Chore, ChoreInstance, ChoreDependency
from users.models import User
from decimal import Decimal
from django.utils import timezone

@pytest.mark.django_db
def test_quick_add_task_complete_later(client):
    user = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
    client.force_login(user)
    
    url = reverse('board:quick_add_task')
    data = {
        'name': 'Test Task Later',
        'description': 'Test Description',
        'points': '15.00',
        'is_difficult': 'false',
        'complete_later': 'true',
        'assignment_type': 'pool'
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert response.json()['success'] is True
    
    chore = Chore.objects.get(name='Test Task Later')
    assert chore.complete_later is True
    
    instance = ChoreInstance.objects.get(chore=chore)
    assert instance.chore.complete_later is True

@pytest.mark.django_db
def test_quick_add_task_spawn_after(client):
    admin = User.objects.create_superuser(username='admin', password='password', email='admin@example.com')
    client.force_login(admin)
    
    parent_chore = Chore.objects.create(name='Parent Chore', points=10, is_pool=True)
    
    url = reverse('board:quick_add_task')
    data = {
        'name': 'Child Task',
        'description': 'Spawns after parent',
        'points': '20.00',
        'is_difficult': 'false',
        'complete_later': 'false',
        'depends_on': parent_chore.id,
        'assignment_type': 'pool' # Should be ignored
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert response.json()['success'] is True
    
    child_chore = Chore.objects.get(name='Child Task')
    assert child_chore.is_active is True
    assert ChoreDependency.objects.filter(chore=child_chore, depends_on=parent_chore).exists()
    
    # Ensure NO instance was created yet
    assert not ChoreInstance.objects.filter(chore=child_chore).exists()
    
    # Now simulate completing the parent chore
    # We need an instance of the parent first
    parent_instance = ChoreInstance.objects.create(
        chore=parent_chore,
        due_at=timezone.now(),
        distribution_at=timezone.now(),
        status=ChoreInstance.ASSIGNED,
        assigned_to=admin
    )
    
    # Complete the parent
    from chores.services import DependencyService
    DependencyService.spawn_dependent_chores(parent_instance, timezone.now())
    
    # Check if child instance was created
    assert ChoreInstance.objects.filter(chore=child_chore).exists()
    child_instance = ChoreInstance.objects.get(chore=child_chore)
    assert child_instance.status == ChoreInstance.ASSIGNED
