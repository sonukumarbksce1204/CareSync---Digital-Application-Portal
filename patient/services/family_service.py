from django.db import transaction
from patient.models import Family, FamilyJoinRequest, FamilyHeadChangeLog, PatientDisease
from django.db.models import Count
from django.utils import timezone

@transaction.atomic
def process_join_request(join_request, reviewing_head, action):
    """
    Safely processes a PENDING request. Attaches patient on APPROVE.
    """
    if action == 'APPROVE':
        join_request.status = 'APPROVED'
        patient = join_request.patient
        patient.family = join_request.family
        patient.family_relationship = join_request.requested_relationship
        patient.save()
    else:
        join_request.status = 'REJECTED'

    join_request.reviewed_by = reviewing_head
    join_request.reviewed_at = timezone.now()
    join_request.save()

@transaction.atomic
def create_family_for_patient(patient):
    """
    Creates a new family and explicitly sets the creator as HEAD.
    """
    family = Family.objects.create(head=patient)
    patient.family = family
    patient.family_relationship = 'HEAD'
    patient.save()
    return family

@transaction.atomic
def change_family_head(family, new_head, changed_by_user, reason):
    """
    Validates and updates the head of a family, ensuring a robust audit trail.
    """
    if not new_head or new_head.family != family:
        raise ValueError("New head must belong to the same family.")
    if new_head.is_deceased:
        raise ValueError("Cannot assign a deceased member as family head.")
        
    old_head = family.head
    if old_head == new_head:
        raise ValueError("Selected member is already the family head.")

    family.head = new_head
    family.save()
    
    new_head.family_relationship = 'HEAD'
    new_head.save()

    if old_head:
        old_head.family_relationship = 'OTHER'
        old_head.save()

    FamilyHeadChangeLog.objects.create(
        family=family,
        old_head=old_head,
        new_head=new_head,
        changed_by=changed_by_user,
        reason=reason
    )
    return True

def get_family_disease_summary(family):
    """
    Aggregates hereditary diseases strictly within the provided family context.
    Returns a queryset with disease__name and an 'occurrences' count.
    """
    return PatientDisease.objects.filter(
        patient__family=family,
        disease__is_hereditary=True,
        is_active=True
    ).values('disease__name').annotate(occurrences=Count('patient')).order_by('-occurrences')
